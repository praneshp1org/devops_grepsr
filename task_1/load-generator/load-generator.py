#!/usr/bin/env python3
"""
Kubernetes Proxy Load Generator

This application generates synthetic traffic through multiple proxy vendors
to simulate crawler pod behavior for monitoring and testing purposes.

Features:
- Multi-vendor proxy rotation (vendor-a, vendor-b, vendor-c)
- HTTP/1.1 and HTTP/2 support
- Prometheus metrics export
- Configurable traffic patterns
- Health checks and monitoring
"""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import click
import psutil
import uvloop
import yaml
from aiohttp import web
from faker import Faker
from prometheus_client import Counter, Histogram, Gauge, start_http_server, generate_latest


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNTER = Counter(
    'load_generator_requests_total',
    'Total HTTP requests made by load generator',
    ['vendor', 'method', 'status_code', 'destination_host']
)

REQUEST_DURATION = Histogram(
    'load_generator_request_duration_seconds',
    'HTTP request duration in seconds',
    ['vendor', 'method', 'destination_host'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0]
)

BANDWIDTH_SENT = Counter(
    'load_generator_bytes_sent_total',
    'Total bytes sent in HTTP requests',
    ['vendor', 'destination_host']
)

BANDWIDTH_RECEIVED = Counter(
    'load_generator_bytes_received_total',
    'Total bytes received in HTTP responses',
    ['vendor', 'destination_host']
)

ACTIVE_CONNECTIONS = Gauge(
    'load_generator_active_connections',
    'Number of active connections',
    ['vendor']
)

ERROR_RATE = Gauge(
    'load_generator_error_rate',
    'Current error rate by vendor',
    ['vendor']
)

PROXY_POOL_HEALTH = Gauge(
    'proxy_pool_health',
    'Health status of proxy pool (1=healthy, 0=unhealthy)',
    ['vendor', 'pool']
)

# System metrics
CPU_USAGE = Gauge('load_generator_cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE = Gauge('load_generator_memory_usage_bytes', 'Memory usage in bytes')


@dataclass
class ProxyVendor:
    """Proxy vendor configuration"""
    name: str
    base_url: str
    pools: List[str]
    auth_headers: Dict[str, str]
    rate_limit: int
    timeout: int
    retry_count: int


@dataclass 
class TrafficPattern:
    """Traffic generation pattern configuration"""
    name: str
    requests_per_second: int
    duration: int
    methods: List[str]
    destinations: List[str]
    payload_sizes: List[int]
    headers: Dict[str, str]


class LoadGenerator:
    """Main load generator class"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.fake = Faker()
        self.session: Optional[aiohttp.ClientSession] = None
        self.vendors = self._initialize_vendors()
        self.patterns = self._initialize_patterns()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': time.time()
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        default_config = {
            'vendors': {
                'vendor-a': {
                    'base_url': 'https://proxy-vendor-a.com',
                    'pools': ['datacenter-us-east', 'datacenter-us-west', 'datacenter-eu'],
                    'auth_headers': {'X-API-Key': 'vendor-a-key'},
                    'rate_limit': 1000,
                    'timeout': 30,
                    'retry_count': 3
                },
                'vendor-b': {
                    'base_url': 'https://proxy-vendor-b.com', 
                    'pools': ['residential-us', 'residential-eu', 'residential-asia'],
                    'auth_headers': {'Authorization': 'Bearer vendor-b-token'},
                    'rate_limit': 500,
                    'timeout': 45,
                    'retry_count': 2
                },
                'vendor-c': {
                    'base_url': 'https://proxy-vendor-c.com',
                    'pools': ['mobile-us', 'mobile-eu', 'mobile-global'],
                    'auth_headers': {'X-Auth-Token': 'vendor-c-token'},
                    'rate_limit': 300,
                    'timeout': 60,
                    'retry_count': 1
                }
            },
            'destinations': [
                'https://httpbin.org',
                'https://jsonplaceholder.typicode.com',
                'https://api.github.com',
                'https://postman-echo.com'
            ],
            'traffic_patterns': {
                'burst': {
                    'requests_per_second': 50,
                    'duration': 300,
                    'methods': ['GET', 'POST'],
                    'payload_sizes': [100, 500, 1000, 5000]
                },
                'steady': {
                    'requests_per_second': 10,
                    'duration': 3600,
                    'methods': ['GET'],
                    'payload_sizes': [100, 200]
                },
                'spike': {
                    'requests_per_second': 200,
                    'duration': 60,
                    'methods': ['GET', 'POST', 'PUT'],
                    'payload_sizes': [50, 100, 500, 1000, 10000]
                }
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return {**default_config, **config}
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return default_config
    
    def _initialize_vendors(self) -> Dict[str, ProxyVendor]:
        """Initialize proxy vendor configurations"""
        vendors = {}
        for name, config in self.config['vendors'].items():
            vendors[name] = ProxyVendor(
                name=name,
                base_url=config['base_url'],
                pools=config['pools'],
                auth_headers=config['auth_headers'],
                rate_limit=config['rate_limit'],
                timeout=config['timeout'],
                retry_count=config['retry_count']
            )
        return vendors
    
    def _initialize_patterns(self) -> Dict[str, TrafficPattern]:
        """Initialize traffic patterns"""
        patterns = {}
        for name, config in self.config['traffic_patterns'].items():
            patterns[name] = TrafficPattern(
                name=name,
                requests_per_second=config['requests_per_second'],
                duration=config['duration'],
                methods=config['methods'],
                destinations=self.config['destinations'],
                payload_sizes=config['payload_sizes'],
                headers=config.get('headers', {})
            )
        return patterns
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create HTTP session with proper configuration"""
        connector = aiohttp.TCPConnector(
            limit=1000,
            limit_per_host=100,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'LoadGenerator/1.0'}
        )
    
    async def _make_request(self, vendor: ProxyVendor, method: str, 
                          destination: str, payload_size: int = 0) -> Dict:
        """Make HTTP request through proxy vendor"""
        start_time = time.time()
        pool = random.choice(vendor.pools)
        
        # Construct request headers including vendor identification
        headers = {
            **vendor.auth_headers,
            'X-Proxy-Vendor': vendor.name,
            'X-Proxy-Pool': pool,
            'X-Request-ID': self.fake.uuid4(),
            'User-Agent': f'Crawler-{vendor.name}-{self.fake.random_int(1000, 9999)}'
        }
        
        # Add payload for POST/PUT requests
        data = None
        if method in ['POST', 'PUT'] and payload_size > 0:
            data = self.fake.text(max_nb_chars=payload_size)
            headers['Content-Type'] = 'application/json'
        
        # Construct URL path
        paths = {
            'https://httpbin.org': ['/get', '/post', '/put', '/delete', '/status/200', '/delay/1'],
            'https://jsonplaceholder.typicode.com': ['/posts', '/users', '/comments', '/albums'],
            'https://api.github.com': ['/users/octocat', '/repos/microsoft/vscode', '/rate_limit'],
            'https://postman-echo.com': ['/get', '/post', '/status/200', '/delay/1']
        }
        
        path = random.choice(paths.get(destination, ['/']))
        url = urljoin(destination, path)
        
        try:
            ACTIVE_CONNECTIONS.labels(vendor=vendor.name).inc()
            
            async with self.session.request(method, url, headers=headers, data=data) as response:
                response_body = await response.read()
                duration = time.time() - start_time
                
                # Record metrics
                REQUEST_COUNTER.labels(
                    vendor=vendor.name,
                    method=method,
                    status_code=str(response.status),
                    destination_host=destination.replace('https://', '').replace('http://', '')
                ).inc()
                
                REQUEST_DURATION.labels(
                    vendor=vendor.name,
                    method=method,
                    destination_host=destination.replace('https://', '').replace('http://', '')
                ).observe(duration)
                
                if data:
                    BANDWIDTH_SENT.labels(
                        vendor=vendor.name,
                        destination_host=destination.replace('https://', '').replace('http://', '')
                    ).inc(len(data.encode('utf-8')))
                
                BANDWIDTH_RECEIVED.labels(
                    vendor=vendor.name,
                    destination_host=destination.replace('https://', '').replace('http://', '')
                ).inc(len(response_body))
                
                # Update pool health based on response
                health_status = 1 if 200 <= response.status < 400 else 0
                PROXY_POOL_HEALTH.labels(vendor=vendor.name, pool=pool).set(health_status)
                
                # Update stats
                self.stats['total_requests'] += 1
                if 200 <= response.status < 400:
                    self.stats['successful_requests'] += 1
                else:
                    self.stats['failed_requests'] += 1
                
                return {
                    'vendor': vendor.name,
                    'pool': pool,
                    'method': method,
                    'url': url,
                    'status': response.status,
                    'duration': duration,
                    'request_size': len(data.encode('utf-8')) if data else 0,
                    'response_size': len(response_body),
                    'timestamp': start_time
                }
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed: {vendor.name} -> {url}: {e}")
            
            # Record error metrics
            REQUEST_COUNTER.labels(
                vendor=vendor.name,
                method=method,
                status_code='error',
                destination_host=destination.replace('https://', '').replace('http://', '')
            ).inc()
            
            PROXY_POOL_HEALTH.labels(vendor=vendor.name, pool=pool).set(0)
            
            self.stats['total_requests'] += 1
            self.stats['failed_requests'] += 1
            
            return {
                'vendor': vendor.name,
                'pool': pool,
                'method': method,
                'url': url,
                'status': 'error',
                'duration': duration,
                'error': str(e),
                'timestamp': start_time
            }
        finally:
            ACTIVE_CONNECTIONS.labels(vendor=vendor.name).dec()
    
    async def _generate_traffic_pattern(self, pattern: TrafficPattern):
        """Generate traffic based on pattern configuration"""
        logger.info(f"Starting traffic pattern: {pattern.name}")
        
        end_time = time.time() + pattern.duration
        request_interval = 1.0 / pattern.requests_per_second
        
        while time.time() < end_time:
            # Select random vendor, method, and destination
            vendor = random.choice(list(self.vendors.values()))
            method = random.choice(pattern.methods)
            destination = random.choice(pattern.destinations)
            payload_size = random.choice(pattern.payload_sizes) if method in ['POST', 'PUT'] else 0
            
            # Create request task
            task = asyncio.create_task(
                self._make_request(vendor, method, destination, payload_size)
            )
            
            # Don't await - let requests run concurrently
            await asyncio.sleep(request_interval)
        
        logger.info(f"Completed traffic pattern: {pattern.name}")
    
    async def _update_system_metrics(self):
        """Update system resource metrics"""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                CPU_USAGE.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                MEMORY_USAGE.set(memory.used)
                
                # Calculate error rates
                for vendor_name in self.vendors.keys():
                    total_requests = sum(
                        REQUEST_COUNTER.labels(vendor=vendor_name, method=m, status_code=s, destination_host=d)._value._value
                        for m in ['GET', 'POST', 'PUT', 'DELETE']
                        for s in ['200', '201', '400', '404', '500', 'error']
                        for d in ['httpbin.org', 'jsonplaceholder.typicode.com', 'api.github.com', 'postman-echo.com']
                    )
                    
                    error_requests = sum(
                        REQUEST_COUNTER.labels(vendor=vendor_name, method=m, status_code=s, destination_host=d)._value._value
                        for m in ['GET', 'POST', 'PUT', 'DELETE']
                        for s in ['400', '404', '500', 'error']
                        for d in ['httpbin.org', 'jsonplaceholder.typicode.com', 'api.github.com', 'postman-echo.com']
                    )
                    
                    error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
                    ERROR_RATE.labels(vendor=vendor_name).set(error_rate)
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error updating system metrics: {e}")
                await asyncio.sleep(10)
    
    async def start_metrics_server(self, port: int = 8080):
        """Start Prometheus metrics HTTP server"""
        app = web.Application()
        
        async def metrics_handler(request):
            return web.Response(text=generate_latest().decode('utf-8'), 
                              content_type='text/plain; version=0.0.4; charset=utf-8')
        
        async def health_handler(request):
            uptime = time.time() - self.stats['start_time']
            health_data = {
                'status': 'healthy',
                'uptime': uptime,
                'total_requests': self.stats['total_requests'],
                'successful_requests': self.stats['successful_requests'],
                'failed_requests': self.stats['failed_requests'],
                'success_rate': (self.stats['successful_requests'] / max(self.stats['total_requests'], 1)) * 100
            }
            return web.json_response(health_data)
        
        async def stats_handler(request):
            vendor_stats = {}
            for vendor_name in self.vendors.keys():
                vendor_stats[vendor_name] = {
                    'active_connections': ACTIVE_CONNECTIONS.labels(vendor=vendor_name)._value._value,
                    'error_rate': ERROR_RATE.labels(vendor=vendor_name)._value._value
                }
            
            return web.json_response({
                'stats': self.stats,
                'vendors': vendor_stats,
                'system': {
                    'cpu_usage': CPU_USAGE._value._value,
                    'memory_usage': MEMORY_USAGE._value._value
                }
            })
        
        app.router.add_get('/metrics', metrics_handler)
        app.router.add_get('/health', health_handler)
        app.router.add_get('/stats', stats_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"Metrics server started on port {port}")
    
    async def run(self, pattern_names: List[str] = None):
        """Run the load generator"""
        if pattern_names is None:
            pattern_names = list(self.patterns.keys())
        
        logger.info("Starting load generator")
        
        # Create HTTP session
        self.session = await self._create_session()
        
        try:
            # Start metrics server
            await self.start_metrics_server()
            
            # Start system metrics updater
            asyncio.create_task(self._update_system_metrics())
            
            # Run traffic patterns
            tasks = []
            for pattern_name in pattern_names:
                if pattern_name in self.patterns:
                    pattern = self.patterns[pattern_name]
                    task = asyncio.create_task(self._generate_traffic_pattern(pattern))
                    tasks.append(task)
                else:
                    logger.warning(f"Unknown pattern: {pattern_name}")
            
            # Wait for all patterns to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                logger.info("No valid patterns specified, running indefinitely")
                while True:
                    await asyncio.sleep(60)
            
        finally:
            if self.session:
                await self.session.close()


@click.command()
@click.option('--config', default='config/config.yaml', help='Configuration file path')
@click.option('--patterns', default='steady', help='Comma-separated list of traffic patterns')
@click.option('--metrics-port', default=8080, help='Metrics server port')
def main(config: str, patterns: str, metrics_port: int):
    """Kubernetes Proxy Load Generator"""
    
    # Set up uvloop for better performance
    uvloop.install()
    
    # Parse patterns
    pattern_list = [p.strip() for p in patterns.split(',')]
    
    # Create and run load generator
    generator = LoadGenerator(config)
    
    try:
        asyncio.run(generator.run(pattern_list))
    except KeyboardInterrupt:
        logger.info("Load generator stopped by user")
    except Exception as e:
        logger.error(f"Load generator error: {e}")
        raise


if __name__ == "__main__":
    main()
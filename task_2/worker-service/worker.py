import asyncio
import asyncpg
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerService:
    def __init__(self):
        self.db_config = {
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'database': os.getenv('DB_NAME', 'microservices_db'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432))
        }
        
    async def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = await asyncpg.connect(**self.db_config)
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    async def process_job(self, job_data):
        """Process a background job"""
        logger.info(f"Processing job: {job_data}")
        
        # Simulate job processing
        await asyncio.sleep(2)
        
        # Update job status in database
        await self.conn.execute(
            "UPDATE jobs SET status = $1, processed_at = $2 WHERE id = $3",
            'completed', datetime.now(), job_data.get('id')
        )
        
        logger.info(f"Job {job_data.get('id')} completed")
        
    async def fetch_pending_jobs(self):
        """Fetch pending jobs from database"""
        try:
            rows = await self.conn.fetch(
                "SELECT * FROM jobs WHERE status = 'pending' LIMIT 10"
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            return []
            
    async def run(self):
        """Main worker loop"""
        await self.connect_db()
        
        while True:
            try:
                jobs = await self.fetch_pending_jobs()
                
                if jobs:
                    for job in jobs:
                        await self.process_job(job)
                else:
                    logger.info("No pending jobs, sleeping...")
                    await asyncio.sleep(10)
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    worker = WorkerService()
    asyncio.run(worker.run())
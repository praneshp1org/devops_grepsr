# Project Structure

microservices-app/
├── .github/
│   └── workflows/
│       ├── ci-cd.yml              # Main CI/CD pipeline
│       └── rollback.yml           # Manual rollback workflow
├── api-service/
│   ├── Dockerfile                 # Production-ready Node.js container
│   ├── package.json               # Node.js dependencies
│   ├── server.js                  # Express API server
│   └── server.test.js             # Unit tests
├── worker-service/
│   ├── Dockerfile                 # Production-ready Python container
│   ├── requirements.txt           # Python dependencies
│   ├── worker.py                  # Background job processor
│   └── test_worker.py             # Unit tests
├── frontend-service/
│   ├── Dockerfile                 # Multi-stage React build
│   ├── nginx.conf                 # Nginx configuration
│   ├── package.json               # React dependencies
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js                 # Main React component
│       ├── App.css                # Styling
│       ├── App.test.js            # Unit tests
│       └── index.js               # React entry point
├── database/
│   └── init.sql                   # Database initialization script
├── k8s/
│   ├── namespace.yaml             # Kubernetes namespace
│   ├── configmap.yaml             # Application configuration
│   ├── secret.yaml                # Sensitive configuration
│   ├── db-init-configmap.yaml     # Database initialization
│   ├── postgres-pvc.yaml          # Persistent volume claim
│   ├── postgres-deployment.yaml   # Database deployment
│   ├── api-deployment.yaml        # API service + HPA
│   ├── worker-deployment.yaml     # Worker service
│   ├── frontend-deployment.yaml   # Frontend + LoadBalancer
│   └── deploy.sh                  # Deployment script
├── docker-compose.yml             # Local development setup
├── .env.example                   # Environment variables template
└── README.md                      # Comprehensive documentation
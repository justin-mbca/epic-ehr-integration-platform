# EPIC EHR Integration System

A comprehensive healthcare interoperability platform implementing HL7, FHIR R4, and EPIC EHR integration capabilities with microservices architecture.

## 🏥 Overview

This system provides a complete healthcare data integration solution with HIPAA-compliant design, enabling seamless communication between healthcare systems, EHRs, and clinical applications.

### Key Features

- **FHIR R4 Server**: Full HAPI FHIR implementation with patient resources
- **HL7 Message Processing**: v2/v3 message handling and transformation
- **EPIC EHR Integration**: Connection Hub compatible interface
- **API Gateway**: OAuth2/JWT authentication with rate limiting
- **Audit Service**: Comprehensive logging and compliance tracking
- **Microservices Architecture**: Docker containerized with health monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │  FHIR Server    │    │ HL7 Processor   │
│   (Node.js)     │    │ (Spring Boot)   │    │   (FastAPI)     │
│   Port: 3000    │    │   Port: 8084    │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
         │ EPIC Connector  │    │ Audit Service   │    │   PostgreSQL    │
         │   (FastAPI)     │    │   (FastAPI)     │    │   Database      │
         │   Port: 8002    │    │   Port: 8003    │    │   Port: 5432    │
         └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                                │
                                                        ┌─────────────────┐
                                                        │      Redis      │
                                                        │     Cache       │
                                                        │   Port: 6379    │
                                                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- 8GB+ RAM recommended
- Ports 3000, 5432, 6379, 8001-8004 available

### Installation

#### Option 1: Quick Start Script (Recommended)
```bash
# Clone the repository
git clone https://github.com/justin-mbca/epic-ehr-integration-platform.git
cd epic-ehr-integration-platform

# Run the interactive quick start script
./quick-start.sh

# Or use command line options
./quick-start.sh start    # Start the system
./quick-start.sh status   # Check status
./quick-start.sh test     # Test endpoints
```

#### Option 2: Manual Installation
```bash
# Clone the repository
git clone https://github.com/justin-mbca/epic-ehr-integration-platform.git
cd epic-ehr-integration-platform

# Start all services
docker compose up -d

# Verify deployment
docker compose ps

# Check service health
curl http://localhost:3000/health        # API Gateway
curl http://localhost:8084/actuator/health  # FHIR Server
curl http://localhost:8001/health        # HL7 Processor
curl http://localhost:8002/health        # EPIC Connector
curl http://localhost:8003/health        # Audit Service
```

## 📋 Services Details

## 🖥️ How to run & view (quick reference)

Start everything (recommended):

```bash
# from repo root
./quick-start.sh
# or manually
docker compose up -d
```

Open in your browser:

- API Gateway (proxy & oauth): http://localhost:3000
   - Health: http://localhost:3000/health
- FHIR Server (direct): http://localhost:8084
   - FHIR metadata (basic auth): http://localhost:8084/fhir/metadata  (user: `admin`, pass: `admin123`)
   - Actuator health: http://localhost:8084/actuator/health

Run the smart_fhir_ingest demo:

```bash
# Unit tests (fast, uses SQLite)
cd projects/smart-fhir-ingest/projects
PYTHONPATH=. python3 -m pytest smart_fhir_ingest/tests/test_ingest.py -q

# Full integration (starts demo Postgres, ingests, verifies, tears down)
make integration-test
```

If ports conflict (host Postgres, Redis), see `docker-compose.dev.yml` for alternate port mappings used for local development (Postgres -> 15432, Redis -> 16379, PgAdmin -> 15050).


### API Gateway (Port 3000)
**Technology**: Node.js + Express  
**Purpose**: Authentication, routing, rate limiting

**Key Endpoints**:
```bash
# Health check
GET /health

# OAuth2 token generation
POST /oauth/token
Content-Type: application/json
{
  "grant_type": "client_credentials",
  "client_id": "epic-test-client",
  "client_secret": "test-secret"
}

# Proxied endpoints (require Bearer token)
GET /fhir/*        # Proxy to FHIR Server
GET /hl7/*         # Proxy to HL7 Processor
GET /epic/*        # Proxy to EPIC Connector
GET /audit/*       # Proxy to Audit Service
```

### FHIR Server (Port 8084)
**Technology**: Spring Boot 3.1.0 + HAPI FHIR 6.6.0  
**Purpose**: FHIR R4 compliant resource server

**Authentication**: HTTP Basic (admin:admin123)

**Key Endpoints**:
```bash
# FHIR Metadata
GET /fhir/metadata

# Patient Resources
GET /fhir/Patient           # List all patients
GET /fhir/Patient/{id}      # Get specific patient

# Health Endpoints
GET /fhir/health           # Custom health check
GET /actuator/health       # Spring Boot actuator
```

**Sample Patient Data**:
- Patient 1: John Doe (ID: EPIC123)
- Patient 2: Jane Smith (ID: EPIC456)

### HL7 Processor (Port 8001)
**Technology**: Python FastAPI  
**Purpose**: HL7 v2/v3 message processing and transformation

### EPIC Connector (Port 8002)
**Technology**: Python FastAPI  
**Purpose**: EPIC EHR integration and Connection Hub interface

### Audit Service (Port 8003)
**Technology**: Python FastAPI  
**Purpose**: Security auditing, compliance logging, and reporting

### Database Services
- **PostgreSQL** (Port 5432): Primary data store
- **Redis** (Port 6379): Caching and session management

## 🔧 Usage Examples

### 1. OAuth2 Authentication Flow

```bash
# Get access token
TOKEN=$(curl -s -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "epic-test-client",
    "client_secret": "test-secret"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 2. FHIR Operations

```bash
# Direct FHIR access (with basic auth)
curl -u admin:admin123 http://localhost:8084/fhir/Patient

# Via API Gateway (with OAuth2)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/fhir/Patient

# Get FHIR metadata
curl -u admin:admin123 http://localhost:8084/fhir/metadata

# Get specific patient
curl -u admin:admin123 http://localhost:8084/fhir/Patient/1
```

### 3. Health Monitoring

```bash
# Check all services
for service in api-gateway fhir-server hl7-processor epic-connector audit-service postgres redis; do
  echo "Checking $service..."
  docker compose ps $service
done
```

## 🔐 Security Configuration

### Authentication
- **API Gateway**: OAuth2 client credentials + JWT tokens
- **FHIR Server**: HTTP Basic authentication
- **Internal Services**: Service-to-service authentication

### Default Credentials
```bash
# FHIR Server
Username: admin
Password: admin123

# OAuth2 Test Client
Client ID: epic-test-client
Client Secret: test-secret

# Database
Username: epic_user
Password: epic_password
Database: epic_db
```

⚠️ **Important**: Change default credentials before production use!

## 🐳 Docker Configuration

### Environment Variables

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `JWT_SECRET` | API Gateway | JWT signing secret | `your-jwt-secret-key` |
| `DB_HOST` | All | Database hostname | `postgres` |
| `DB_USER` | All | Database username | `epic_user` |
| `DB_PASSWORD` | All | Database password | `epic_password` |
| `FHIR_SERVER_URL` | API Gateway | FHIR server URL | `http://fhir-server:8084` |

### Service Dependencies
```yaml
API Gateway → PostgreSQL, Redis
FHIR Server → PostgreSQL  
HL7 Processor → PostgreSQL, Redis
EPIC Connector → PostgreSQL, Redis
Audit Service → PostgreSQL, Redis
```

## 📊 Monitoring & Health Checks

### Service Status
```bash
# Container status
docker compose ps

# Service logs
docker compose logs [service-name]

# Health endpoints
curl http://localhost:3000/health
curl http://localhost:8084/actuator/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Database Health
```bash
# PostgreSQL connection test
docker compose exec postgres psql -U epic_user -d epic_db -c "SELECT version();"

# Redis connection test
docker compose exec redis redis-cli ping
```

## 🛠️ Development

### Local Development Setup

1. **Start infrastructure only**
   ```bash
   docker compose up -d postgres redis
   ```

2. **Run services locally**
   ```bash
   # FHIR Server
   cd services/fhir-server
   ./mvnw spring-boot:run

   # API Gateway
   cd services/api-gateway
   npm install
   npm start

   # Python services
   cd services/hl7-processor
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8001
   ```

### Building Individual Services
```bash
# FHIR Server
docker compose build fhir-server

# API Gateway
docker compose build api-gateway

# Python services
docker compose build hl7-processor epic-connector audit-service
```

## 🔍 Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep -E ':(3000|5432|6379|8001|8002|8003|8084)'
   ```

2. **Service won't start**
   ```bash
   # Check logs
   docker compose logs [service-name]
   
   # Restart service
   docker compose restart [service-name]
   ```

3. **Database connection issues**
   ```bash
   # Verify database is running
   docker compose exec postgres pg_isready
   
   # Check database connectivity
   docker compose exec postgres psql -U epic_user -d epic_db -c "SELECT 1;"
   ```

4. **FHIR Server 502 errors**
   ```bash
   # Check FHIR server health
   curl -u admin:admin123 http://localhost:8084/actuator/health
   
   # Restart FHIR server
   docker compose restart fhir-server
   ```

### Logs and Debugging
```bash
# All services logs
docker compose logs -f

# Specific service logs
docker compose logs -f fhir-server

# Follow logs with timestamps
docker compose logs -f --timestamps api-gateway
```

## 📚 Documentation

### Core Documentation
- **[API Gateway Guide](docs/API_GATEWAY.md)** - OAuth2, JWT, proxy configuration
- **[FHIR Server Guide](docs/FHIR_SERVER.md)** - HAPI FHIR, patient resources, endpoints
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Docker Compose, Kubernetes, production setup
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues, diagnostics, recovery

### Quick Reference

#### FHIR R4 Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/fhir/metadata` | GET | FHIR CapabilityStatement | Basic |
| `/fhir/Patient` | GET | List all patients | Basic |
| `/fhir/Patient/{id}` | GET | Get patient by ID | Basic |
| `/fhir/health` | GET | Service health check | Basic |

#### OAuth2 Endpoints

| Endpoint | Method | Description | Body |
|----------|--------|-------------|------|
| `/oauth/token` | POST | Get access token | `grant_type`, `client_id`, `client_secret` |

#### Proxy Endpoints (via API Gateway)

All backend services are accessible through the API Gateway with OAuth2 authentication:

- `/fhir/*` → FHIR Server (Port 8084)
- `/hl7/*` → HL7 Processor (Port 8001)  
- `/epic/*` → EPIC Connector (Port 8002)
- `/audit/*` → Audit Service (Port 8003)

## 🚀 Production Deployment

### Pre-Production Checklist

- [ ] Change all default passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set up proper JWT secrets
- [ ] Configure external database
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (ELK stack)
- [ ] Set up backup strategies
- [ ] Configure network security
- [ ] Implement HIPAA compliance measures

### Scaling Considerations

- Use Kubernetes for orchestration
- Implement database connection pooling
- Add Redis clustering for high availability
- Configure load balancing
- Set up auto-scaling policies

## 📄 Compliance & Standards

- **FHIR R4**: Full compatibility with FHIR R4 specification
- **HL7**: Support for HL7 v2.x and v3 messages
- **HIPAA Ready**: Architecture supports HIPAA compliance requirements
- **Security**: OAuth2, JWT, rate limiting, audit logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review service logs
- Create an issue in the repository

## 📋 Changelog

### Version 1.0.0 (Current)
- ✅ FHIR R4 server with patient resources
- ✅ OAuth2 API Gateway with JWT authentication
- ✅ HL7 message processing service
- ✅ EPIC EHR connector service
- ✅ Audit and compliance service
- ✅ PostgreSQL and Redis integration
- ✅ Docker Compose orchestration
- ✅ Health monitoring and logging

## 📄 License

[Add your license information here]

---

**Built with ❤️ for Healthcare Interoperability**

## 🧪 Project demos

This repository now includes small, self-contained demos and integration tests you can run locally or in CI to demonstrate data-engineering skills:

- smart_fhir_ingest: a Python demo that parses a FHIR Patient bundle and ingests patient rows into a target database.
   - Local mode: writes to SQLite (used by unit tests).
   - Dev mode: docker-compose with a demo Postgres (exposed on host port 15433) for quick integration runs.
   - CI mode: a GitHub Actions workflow (`.github/workflows/integration-runner.yml`) runs the integration end-to-end using Actions `services.postgres`.
   - Files of interest:
      - `projects/smart-fhir-ingest/projects/smart_fhir_ingest/ingest.py` — ingestion logic (SQLite + Postgres support)
      - `projects/smart-fhir-ingest/projects/integration_test_runner.py` — runs compose -> ingest -> verify -> teardown
      - `projects/smart-fhir-ingest/projects/docker-compose.yml` — demo Postgres for local runs
      - `projects/smart-fhir-ingest/projects/Makefile` — `make integration-test` runs the end-to-end demo locally

## 🗣️ Interview talking points (senior data engineer)

Use these concise bullets to explain this project in interviews — each is backed by runnable code in the repo:

- Built a reproducible local integration environment using Docker Compose and health-checked services (Postgres, Redis) to emulate production dependencies and validate end-to-end data flows.
- Implemented a lightweight SMART-on-FHIR ingestion demo that parses FHIR R4 bundles and maps Patient resources to an analytics schema, demonstrating domain modeling and ETL design.
- Added idempotent ingestion into Postgres with upsert semantics (ON CONFLICT) and a SQLite fallback for fast unit tests — shows concerns for testability and production safety.
- Automated integration tests: `integration_test_runner.py` starts services, waits for readiness (`pg_isready`), runs ingestion, verifies results, and tears down — shows CI-first testing and repeatable pipelines.
- CI-native integration: created a GitHub Actions workflow that uses `services.postgres` to run the same end-to-end test without docker-compose, proving the system works in ephemeral CI environments.
- Minimal Airflow DAG scaffold that demonstrates how to schedule the ingestion as a repeatable job, and a dbt scaffold for simple downstream transformations — indicates orchestration and analytics engineering awareness.
- Security and deployment considerations: handled secrets and credentials via environment variables and provided guidance to replace defaults before production; can discuss how to swap to Vault or a secrets manager.
- Observability: added health endpoints and health checks in compose/workflows; can discuss metrics, logging strategy, and alerting paths for production readiness.
- Troubleshooting and reliability: demonstrated iterative debugging (fixing build-time Java errors, container conflicts, and port remapping) and automated smoke-tests to catch regressions earlier.

Quick rehearsal lines for interviews:

"I built a small, production-like integration platform that processes FHIR bundles and writes to Postgres. I focused on testability — unit tests run against SQLite, and an automated integration test runs locally with docker-compose and in CI using Actions services. The pipeline is idempotent, health-checked, and easily schedulable with Airflow; dbt scaffolding shows how I'd implement analytics transformations next." 

# API Gateway Documentation

## Overview

The API Gateway serves as the central entry point for the EPIC EHR Integration System, providing authentication, authorization, rate limiting, and request routing to backend microservices.

## Technology Stack

- **Runtime**: Node.js 18
- **Framework**: Express.js
- **Authentication**: OAuth2 + JWT
- **Security**: Helmet, CORS, Rate Limiting
- **Proxy**: http-proxy-middleware

## Configuration

### Environment Variables

```bash
NODE_ENV=development
JWT_SECRET=your-jwt-secret-key
DB_HOST=postgres
DB_PORT=5432
DB_NAME=epic_ehr
DB_USER=epic_user
DB_PASSWORD=epic_password
REDIS_URL=redis://redis:6379
FHIR_SERVER_URL=http://fhir-server:8084
HL7_PROCESSOR_URL=http://hl7-processor:8001
EPIC_CONNECTOR_URL=http://epic-connector:8002
AUDIT_SERVICE_URL=http://audit-service:8003
```

## API Endpoints

### Public Endpoints

#### Health Check
```
GET /health
```
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-23T04:58:48.040Z",
  "version": "1.0.0"
}
```

#### OAuth2 Token
```
POST /oauth/token
Content-Type: application/json
```
**Request Body**:
```json
{
  "grant_type": "client_credentials",
  "client_id": "epic-test-client",
  "client_secret": "test-secret"
}
```
**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "fhir:read fhir:write hl7:process"
}
```

### Protected Endpoints (require Bearer token)

#### FHIR Proxy
```
ALL /fhir/*
Authorization: Bearer <token>
```
Proxies to FHIR Server (port 8084) with automatic basic auth injection.

#### HL7 Processor Proxy
```
ALL /hl7/*
Authorization: Bearer <token>
```
Proxies to HL7 Processor service (port 8001).

#### EPIC Connector Proxy
```
ALL /epic/*
Authorization: Bearer <token>
```
Proxies to EPIC Connector service (port 8002).

#### Audit Service Proxy
```
ALL /audit/*
Authorization: Bearer <token>
```
Proxies to Audit Service (port 8003).

## Security Features

### Rate Limiting
- **Window**: 15 minutes
- **Limit**: 100 requests per IP
- **Response**: 429 Too Many Requests

### CORS Configuration
- **Origins**: Configurable via `ALLOWED_ORIGINS`
- **Credentials**: Enabled
- **Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Headers**: Content-Type, Authorization, X-Requested-With

### Helmet Security Headers
- Content Security Policy
- HSTS (HTTPS Strict Transport Security)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Cross-Origin policies

### JWT Authentication
- **Algorithm**: HS256
- **Expiry**: 1 hour
- **Issuer**: epic-ehr-gateway
- **Scope**: fhir:read fhir:write hl7:process

## Usage Examples

### Getting an Access Token
```bash
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "epic-test-client",
    "client_secret": "test-secret"
  }'
```

### Using the Token
```bash
# Store token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Access FHIR resources
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/fhir/Patient

# Access HL7 processor
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/hl7/health

# Access EPIC connector
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/epic/health

# Access audit service
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/audit/health
```

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Access token required"
}
```

### 403 Forbidden
```json
{
  "error": "Invalid or expired token"
}
```

### 429 Too Many Requests
```json
{
  "error": "Too many requests from this IP, please try again later."
}
```

### 502 Bad Gateway
```json
{
  "error": "FHIR service temporarily unavailable",
  "message": "Connection timeout"
}
```

## Logging and Auditing

### Log Format
```json
{
  "timestamp": "2025-09-23T04:58:48.040Z",
  "level": "info",
  "message": "API Access",
  "ip": "192.168.1.100",
  "method": "GET",
  "url": "/fhir/Patient",
  "userAgent": "curl/8.1.2",
  "userId": "client-id"
}
```

### Audit Events
- OAuth2 token issuance
- API endpoint access
- Proxy requests to backend services
- Authentication failures
- Rate limit violations

## Development

### Local Development
```bash
cd services/api-gateway
npm install
npm run dev
```

### Testing
```bash
npm test
npm run test:watch
```

### Linting
```bash
npm run lint
npm run lint:fix
```

## Docker

### Build
```bash
docker compose build api-gateway
```

### Run
```bash
docker compose up api-gateway -d
```

### Logs
```bash
docker compose logs api-gateway -f
```

## Health Monitoring

The API Gateway includes health checks:

### Docker Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Monitoring Endpoints
- `/health` - Application health status
- Internal metrics available for Prometheus integration

## Performance Considerations

### Connection Pooling
- HTTP agent keep-alive enabled
- Connection reuse for backend services
- Configurable timeout settings

### Caching
- JWT verification caching
- Redis integration for session management
- Rate limiting data stored in Redis

### Scaling
- Stateless design for horizontal scaling
- Load balancer compatible
- Session data externalized to Redis

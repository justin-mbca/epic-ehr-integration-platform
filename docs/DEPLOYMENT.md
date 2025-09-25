# Deployment Guide

## Overview

This guide covers deployment options for the EPIC EHR Integration System, from development to production environments.

## Table of Contents

1. [Development Deployment](#development-deployment)
2. [Docker Compose Deployment](#docker-compose-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Production Considerations](#production-considerations)
5. [Security Hardening](#security-hardening)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Backup and Recovery](#backup-and-recovery)

## Development Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 50GB disk space

### Quick Start

1. **Clone and Start**
   ```bash
   git clone <repository-url>
   cd Upwork1
   docker compose up -d
   ```

2. **Verify Deployment**
   ```bash
   # Check all services
   docker compose ps
   
   # Test endpoints
   curl http://localhost:3000/health
   curl -u admin:admin123 http://localhost:8084/fhir/health
   ```

3. **View Logs**
   ```bash
   docker compose logs -f
   ```

## Docker Compose Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: epic-postgres-prod
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 30s
      timeout: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: epic-redis-prod
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: epic-api-gateway-prod
    ports:
      - "443:3000"  # Use HTTPS in production
    environment:
      NODE_ENV: production
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
      FHIR_SERVER_URL: http://fhir-server:8084
      HL7_PROCESSOR_URL: http://hl7-processor:8001
      EPIC_CONNECTOR_URL: http://epic-connector:8002
      AUDIT_SERVICE_URL: http://audit-service:8003
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  fhir-server:
    build:
      context: ./services/fhir-server
      dockerfile: Dockerfile
    container_name: epic-fhir-server-prod
    ports:
      - "8084:8084"
    environment:
      SPRING_PROFILES_ACTIVE: production
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/${DB_NAME}
      SPRING_DATASOURCE_USERNAME: ${DB_USER}
      SPRING_DATASOURCE_PASSWORD: ${DB_PASSWORD}
      SPRING_JPA_HIBERNATE_DDL_AUTO: validate
      FHIR_USERNAME: ${FHIR_USERNAME}
      FHIR_PASSWORD: ${FHIR_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "-u", "${FHIR_USERNAME}:${FHIR_PASSWORD}", "http://localhost:8084/actuator/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: epic-network-prod
```

### Environment Variables for Production

Create `.env.prod`:

```bash
# Database Configuration
DB_NAME=epic_ehr_prod
DB_USER=epic_user_prod
DB_PASSWORD=your_secure_db_password

# FHIR Server Authentication
FHIR_USERNAME=fhir_admin
FHIR_PASSWORD=your_secure_fhir_password

# JWT Configuration
JWT_SECRET=your_super_secure_jwt_secret_key_at_least_32_chars

# SSL Configuration
SSL_CERTIFICATE=/path/to/certificate.crt
SSL_PRIVATE_KEY=/path/to/private.key

# External Services
EPIC_CONNECTION_HUB_URL=https://your-epic-hub.example.com
SMTP_HOST=smtp.your-domain.com
SMTP_PORT=587
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your_smtp_password
```

### Deploy Production

```bash
# Deploy with production configuration
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Scale services if needed
docker compose -f docker-compose.prod.yml up -d --scale api-gateway=2
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.20+
- kubectl configured
- Helm 3.0+ (optional)

### Namespace Setup

```bash
kubectl create namespace epic-ehr
kubectl config set-context --current --namespace=epic-ehr
```

### ConfigMaps and Secrets

#### Database Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-secret
  namespace: epic-ehr
type: Opaque
data:
  username: ZXBpY191c2Vy  # base64 encoded
  password: eW91cl9zZWN1cmVfcGFzc3dvcmQ=  # base64 encoded
```

#### Application ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: epic-ehr
data:
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "epic_ehr"
  REDIS_URL: "redis://redis-service:6379"
  FHIR_SERVER_URL: "http://fhir-server-service:8084"
```

### PostgreSQL Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: epic-ehr
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DB_NAME
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: epic-ehr
spec:
  selector:
    app: postgres
  ports:
  - protocol: TCP
    port: 5432
    targetPort: 5432
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: epic-ehr
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### FHIR Server Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fhir-server
  namespace: epic-ehr
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fhir-server
  template:
    metadata:
      labels:
        app: fhir-server
    spec:
      containers:
      - name: fhir-server
        image: your-registry/epic-fhir-server:latest
        ports:
        - containerPort: 8084
        env:
        - name: SPRING_PROFILES_ACTIVE
          value: "kubernetes"
        - name: SPRING_DATASOURCE_URL
          value: "jdbc:postgresql://postgres-service:5432/epic_ehr"
        - name: SPRING_DATASOURCE_USERNAME
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: username
        - name: SPRING_DATASOURCE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: password
        livenessProbe:
          httpGet:
            path: /actuator/health
            port: 8084
            httpHeaders:
            - name: Authorization
              value: Basic YWRtaW46YWRtaW4xMjM=
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /actuator/health
            port: 8084
            httpHeaders:
            - name: Authorization
              value: Basic YWRtaW46YWRtaW4xMjM=
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: fhir-server-service
  namespace: epic-ehr
spec:
  selector:
    app: fhir-server
  ports:
  - protocol: TCP
    port: 8084
    targetPort: 8084
```

### API Gateway Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: epic-ehr
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: your-registry/epic-api-gateway:latest
        ports:
        - containerPort: 3000
        envFrom:
        - configMapRef:
            name: app-config
        env:
        - name: NODE_ENV
          value: "production"
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: epic-ehr
spec:
  selector:
    app: api-gateway
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: epic-ehr-ingress
  namespace: epic-ehr
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.epic-ehr.your-domain.com
    secretName: epic-ehr-tls
  rules:
  - host: api.epic-ehr.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway-service
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -w

# Check services
kubectl get services

# Check ingress
kubectl get ingress
```

## Production Considerations

### Resource Requirements

#### Minimum Production Resources

| Service | CPU | Memory | Storage |
|---------|-----|--------|---------|
| API Gateway | 500m | 512Mi | - |
| FHIR Server | 1000m | 1Gi | - |
| HL7 Processor | 500m | 512Mi | - |
| EPIC Connector | 500m | 512Mi | - |
| Audit Service | 250m | 256Mi | - |
| PostgreSQL | 1000m | 2Gi | 50Gi |
| Redis | 250m | 256Mi | 10Gi |

#### Recommended Production Resources

| Service | CPU | Memory | Storage |
|---------|-----|--------|---------|
| API Gateway | 1000m | 1Gi | - |
| FHIR Server | 2000m | 2Gi | - |
| HL7 Processor | 1000m | 1Gi | - |
| EPIC Connector | 1000m | 1Gi | - |
| Audit Service | 500m | 512Mi | - |
| PostgreSQL | 2000m | 4Gi | 200Gi |
| Redis | 500m | 1Gi | 20Gi |

### High Availability

#### Database High Availability

1. **PostgreSQL Primary-Replica Setup**
   ```yaml
   # Primary database
   postgres-primary:
     image: postgres:15-alpine
     environment:
       POSTGRES_REPLICATION_MODE: master
       POSTGRES_REPLICATION_USER: replica_user
       POSTGRES_REPLICATION_PASSWORD: replica_password
   
   # Replica database
   postgres-replica:
     image: postgres:15-alpine
     environment:
       POSTGRES_REPLICATION_MODE: slave
       POSTGRES_MASTER_SERVICE: postgres-primary
       POSTGRES_REPLICATION_USER: replica_user
       POSTGRES_REPLICATION_PASSWORD: replica_password
   ```

2. **Redis Cluster**
   ```yaml
   redis-cluster:
     image: redis:7-alpine
     command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf
   ```

#### Application High Availability

1. **Multiple Replicas**
   - API Gateway: 3+ replicas
   - FHIR Server: 2+ replicas
   - Other services: 2+ replicas

2. **Load Balancing**
   - Use Kubernetes services
   - Configure ingress controllers
   - Health check endpoints

3. **Auto-scaling**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: api-gateway-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: api-gateway
     minReplicas: 3
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

## Security Hardening

### Network Security

1. **Network Policies**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: epic-ehr-network-policy
   spec:
     podSelector:
       matchLabels:
         app: fhir-server
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: api-gateway
       ports:
       - protocol: TCP
         port: 8084
   ```

2. **TLS/SSL Configuration**
   - Use cert-manager for automatic certificate management
   - Configure HTTPS-only access
   - Implement mutual TLS for service-to-service communication

3. **Firewall Rules**
   - Restrict database access to application subnets only
   - Block direct external access to internal services
   - Implement DDoS protection

### Authentication and Authorization

1. **OAuth2/OIDC Integration**
   ```yaml
   # Example with Keycloak
   keycloak:
     image: quay.io/keycloak/keycloak:latest
     environment:
       KEYCLOAK_ADMIN: admin
       KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_PASSWORD}
   ```

2. **RBAC Configuration**
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: epic-ehr-reader
   rules:
   - apiGroups: [""]
     resources: ["pods", "services"]
     verbs: ["get", "list"]
   ```

3. **Service Mesh (Istio)**
   ```yaml
   apiVersion: security.istio.io/v1beta1
   kind: AuthorizationPolicy
   metadata:
     name: fhir-server-policy
   spec:
     selector:
       matchLabels:
         app: fhir-server
     rules:
     - from:
       - source:
           principals: ["cluster.local/ns/epic-ehr/sa/api-gateway"]
   ```

### Data Security

1. **Encryption at Rest**
   - Database encryption
   - Volume encryption
   - Secret encryption in etcd

2. **Encryption in Transit**
   - TLS 1.3 for all communications
   - Certificate rotation
   - mTLS for internal services

3. **Secrets Management**
   ```yaml
   # Using external secrets operator
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: vault-backend
   spec:
     provider:
       vault:
         server: "https://vault.example.com"
         path: "secret"
         auth:
           kubernetes:
             mountPath: "kubernetes"
             role: "epic-ehr"
   ```

## Monitoring and Logging

### Prometheus Monitoring

1. **ServiceMonitor Configuration**
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: epic-ehr-metrics
   spec:
     selector:
       matchLabels:
         app: fhir-server
     endpoints:
     - port: metrics
       interval: 30s
       path: /actuator/prometheus
   ```

2. **Grafana Dashboards**
   - JVM metrics dashboard
   - Database performance dashboard
   - API response time dashboard
   - Error rate dashboard

### Centralized Logging

1. **ELK Stack Configuration**
   ```yaml
   # Filebeat DaemonSet
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: filebeat
   spec:
     template:
       spec:
         containers:
         - name: filebeat
           image: elastic/filebeat:8.0.0
           volumeMounts:
           - name: varlog
             mountPath: /var/log
           - name: varlibdockercontainers
             mountPath: /var/lib/docker/containers
   ```

2. **Log Aggregation**
   - Structured JSON logging
   - Log correlation IDs
   - Audit trail logging
   - Error alerting

### Health Checks and Alerting

1. **Health Check Configuration**
   ```yaml
   livenessProbe:
     httpGet:
       path: /actuator/health/liveness
       port: 8084
     initialDelaySeconds: 60
     periodSeconds: 30
     timeoutSeconds: 5
     failureThreshold: 3
   
   readinessProbe:
     httpGet:
       path: /actuator/health/readiness
       port: 8084
     initialDelaySeconds: 30
     periodSeconds: 10
     timeoutSeconds: 5
     failureThreshold: 3
   ```

2. **Alerting Rules**
   ```yaml
   # Prometheus alerting rules
   groups:
   - name: epic-ehr-alerts
     rules:
     - alert: HighErrorRate
       expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
       for: 5m
       labels:
         severity: warning
       annotations:
         summary: "High error rate detected"
   ```

## Backup and Recovery

### Database Backup

1. **Automated Backups**
   ```bash
   # PostgreSQL backup script
   #!/bin/bash
   BACKUP_DIR="/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   pg_dump -h postgres-service -U epic_user -d epic_ehr > \
     $BACKUP_DIR/epic_ehr_$DATE.sql
   
   # Upload to cloud storage
   aws s3 cp $BACKUP_DIR/epic_ehr_$DATE.sql \
     s3://epic-ehr-backups/database/
   ```

2. **Point-in-Time Recovery**
   ```yaml
   # PostgreSQL with WAL-E
   postgres:
     image: postgres:15-alpine
     environment:
       POSTGRES_INITDB_WALDIR: /var/lib/postgresql/wal
       archive_mode: "on"
       archive_command: "wal-e wal-push %p"
   ```

### Application Backup

1. **Configuration Backup**
   ```bash
   # Backup Kubernetes configurations
   kubectl get all -o yaml > epic-ehr-backup.yaml
   kubectl get configmaps -o yaml >> epic-ehr-backup.yaml
   kubectl get secrets -o yaml >> epic-ehr-backup.yaml
   ```

2. **Volume Snapshots**
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshot
   metadata:
     name: postgres-snapshot
   spec:
     source:
       persistentVolumeClaimName: postgres-pvc
     volumeSnapshotClassName: csi-snapclass
   ```

### Disaster Recovery

1. **Multi-Region Setup**
   - Primary region: Active deployment
   - Secondary region: Standby deployment
   - Database replication between regions

2. **Recovery Procedures**
   ```bash
   # Database recovery
   psql -h postgres -U epic_user -d epic_ehr < backup.sql
   
   # Application recovery
   kubectl apply -f epic-ehr-backup.yaml
   
   # Verify recovery
   ./scripts/health-check.sh
   ```

3. **RTO/RPO Targets**
   - Recovery Time Objective (RTO): < 1 hour
   - Recovery Point Objective (RPO): < 15 minutes
   - Data backup frequency: Every 6 hours
   - Configuration backup: Daily

This deployment guide provides comprehensive coverage for deploying the EPIC EHR Integration System across different environments with proper security, monitoring, and recovery procedures.

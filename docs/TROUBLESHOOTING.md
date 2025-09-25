# Troubleshooting Guide

## Common Issues and Solutions

### 1. Port Conflicts

**Problem**: Services fail to start with "port already in use" errors.

**Solution**:
```bash
# Check what's using the ports
netstat -tulpn | grep -E ':(3000|5432|6379|8001|8002|8003|8084)'

# Kill processes using required ports (be careful!)
sudo lsof -ti:3000 | xargs kill -9
sudo lsof -ti:8084 | xargs kill -9

# Or change ports in docker-compose.yml
```

### 2. Database Connection Issues

**Problem**: Services can't connect to PostgreSQL.

**Symptoms**:
- `Connection refused` errors
- `authentication failed` messages
- Services stuck in restart loop

**Solutions**:

1. **Check Database Status**:
   ```bash
   docker compose ps postgres
   docker compose logs postgres
   ```

2. **Verify Database Health**:
   ```bash
   docker compose exec postgres pg_isready -U epic_user
   docker compose exec postgres psql -U epic_user -d epic_db -c "SELECT 1;"
   ```

3. **Reset Database**:
   ```bash
   docker compose down
   docker volume rm upwork1_postgres_data
   docker compose up -d postgres
   ```

### 3. FHIR Server Won't Start

**Problem**: FHIR server container exits or shows unhealthy status.

**Common Causes**:
- Database not ready
- Invalid configuration
- Memory issues
- Port conflicts

**Solutions**:

1. **Check Logs**:
   ```bash
   docker compose logs fhir-server
   ```

2. **Verify Dependencies**:
   ```bash
   # Ensure database is healthy first
   docker compose ps postgres
   ```

3. **Memory Issues**:
   ```bash
   # Increase Docker memory limit to 8GB+
   # Check current memory usage
   docker stats
   ```

4. **Configuration Issues**:
   ```bash
   # Check environment variables
   docker compose exec fhir-server env | grep -E "(SPRING|DB)"
   ```

### 4. Authentication Failures

**Problem**: 401/403 errors when accessing services.

**For FHIR Server**:
```bash
# Test basic auth
curl -v -u admin:admin123 http://localhost:8084/fhir/health

# Check credentials in logs
docker compose logs fhir-server | grep -i auth
```

**For API Gateway OAuth2**:
```bash
# Test token generation
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "epic-test-client",
    "client_secret": "test-secret"
  }'

# Check JWT secret
docker compose exec api-gateway env | grep JWT_SECRET
```

### 5. API Gateway Proxy Errors

**Problem**: 502 Bad Gateway errors when accessing `/fhir/*` endpoints.

**Solutions**:

1. **Check Service Connectivity**:
   ```bash
   # Test internal network connectivity
   docker compose exec api-gateway ping fhir-server
   ```

2. **Verify FHIR Server URL**:
   ```bash
   docker compose exec api-gateway env | grep FHIR_SERVER_URL
   ```

3. **Check Proxy Configuration**:
   ```bash
   docker compose logs api-gateway | grep -i proxy
   ```

### 6. Container Health Check Failures

**Problem**: Services showing as unhealthy in `docker compose ps`.

**Solutions**:

1. **Check Health Check Endpoint**:
   ```bash
   # For API Gateway
   curl http://localhost:3000/health
   
   # For FHIR Server
   curl -u admin:admin123 http://localhost:8084/actuator/health
   ```

2. **Review Health Check Configuration**:
   ```bash
   # Check docker-compose.yml health check settings
   grep -A 10 "healthcheck:" docker-compose.yml
   ```

3. **Adjust Health Check Timing**:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
     interval: 30s
     timeout: 10s
     retries: 5
     start_period: 60s  # Increase if services are slow to start
   ```

### 7. Performance Issues

**Problem**: Slow response times or timeouts.

**Monitoring**:
```bash
# Check resource usage
docker stats

# Monitor logs for slow queries
docker compose logs | grep -i "slow\|timeout\|performance"
```

**Solutions**:

1. **Database Performance**:
   ```sql
   -- Connect to database and check connections
   SELECT * FROM pg_stat_activity;
   
   -- Check for long-running queries
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
   ```

2. **Increase Resources**:
   ```yaml
   # In docker-compose.yml
   services:
     fhir-server:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '2'
   ```

### 8. Network Connectivity Issues

**Problem**: Services can't communicate with each other.

**Solutions**:

1. **Check Docker Network**:
   ```bash
   docker network ls
   docker network inspect upwork1_epic-network
   ```

2. **Test Service Discovery**:
   ```bash
   # From one container, ping another
   docker compose exec api-gateway ping postgres
   docker compose exec api-gateway ping fhir-server
   ```

3. **Check Firewall/Security Groups**:
   - Ensure Docker has proper network access
   - Check host firewall rules
   - Verify cloud security groups if applicable

### 9. SSL/Certificate Issues

**Problem**: Certificate errors in production deployment.

**Solutions**:

1. **Check Certificate Validity**:
   ```bash
   openssl x509 -in certificate.crt -text -noout
   ```

2. **Verify Certificate Chain**:
   ```bash
   openssl verify -CAfile ca-bundle.crt certificate.crt
   ```

3. **Test SSL Connection**:
   ```bash
   openssl s_client -connect your-domain.com:443 -servername your-domain.com
   ```

### 10. Data Persistence Issues

**Problem**: Data is lost when containers restart.

**Solutions**:

1. **Check Volume Mounts**:
   ```bash
   docker volume ls
   docker volume inspect upwork1_postgres_data
   ```

2. **Verify Persistent Data**:
   ```bash
   # Check if database data persists
   docker compose down
   docker compose up -d postgres
   docker compose exec postgres psql -U epic_user -d epic_db -c "\dt"
   ```

## Diagnostic Commands

### System Overview
```bash
# Quick system status
./quick-start.sh status

# Detailed container information
docker compose ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"

# Resource usage
docker stats --no-stream
```

### Service-Specific Diagnostics

#### API Gateway
```bash
# Check logs
docker compose logs api-gateway --tail=50

# Test endpoints
curl http://localhost:3000/health
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "client_credentials", "client_id": "epic-test-client", "client_secret": "test-secret"}'

# Check environment
docker compose exec api-gateway env
```

#### FHIR Server
```bash
# Check logs
docker compose logs fhir-server --tail=50

# Test endpoints
curl -u admin:admin123 http://localhost:8084/fhir/health
curl -u admin:admin123 http://localhost:8084/actuator/health

# Check JVM status
docker compose exec fhir-server jps -v
```

#### Database
```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Connect to database
docker compose exec postgres psql -U epic_user -d epic_db

# Check database size and connections
docker compose exec postgres psql -U epic_user -d epic_db -c "
  SELECT pg_database_size('epic_db');
  SELECT count(*) FROM pg_stat_activity;
"
```

#### Redis
```bash
# Check Redis status
docker compose exec redis redis-cli ping

# Check Redis info
docker compose exec redis redis-cli info

# Monitor Redis commands
docker compose exec redis redis-cli monitor
```

## Performance Tuning

### Database Optimization

1. **Connection Pooling**:
   ```yaml
   # In application.yml
   spring:
     datasource:
       hikari:
         maximum-pool-size: 20
         minimum-idle: 5
         connection-timeout: 30000
         idle-timeout: 600000
   ```

2. **Database Configuration**:
   ```sql
   -- PostgreSQL configuration
   ALTER SYSTEM SET shared_buffers = '256MB';
   ALTER SYSTEM SET effective_cache_size = '1GB';
   ALTER SYSTEM SET maintenance_work_mem = '64MB';
   SELECT pg_reload_conf();
   ```

### JVM Tuning

```dockerfile
# In FHIR server Dockerfile
ENV JAVA_OPTS="-Xmx2g -Xms1g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
```

### Redis Configuration

```yaml
# In docker-compose.yml
redis:
  image: redis:7-alpine
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Monitoring and Alerts

### Log Analysis
```bash
# Error analysis
docker compose logs | grep -i error | tail -20

# Performance analysis
docker compose logs | grep -E "(slow|timeout|performance)" | tail -20

# Authentication analysis
docker compose logs | grep -E "(auth|login|token)" | tail -20
```

### Health Monitoring Script
```bash
#!/bin/bash
# health-monitor.sh

services=(api-gateway fhir-server hl7-processor epic-connector audit-service postgres redis)

for service in "${services[@]}"; do
    status=$(docker compose ps $service --format "{{.Status}}")
    if [[ $status == *"healthy"* ]] || [[ $status == *"Up"* ]]; then
        echo "✅ $service: OK"
    else
        echo "❌ $service: $status"
    fi
done
```

## Recovery Procedures

### Complete System Recovery
```bash
# 1. Stop everything
docker compose down --volumes

# 2. Clean up
docker system prune -f
docker volume prune -f

# 3. Rebuild and start
docker compose build --no-cache
docker compose up -d

# 4. Wait and test
sleep 60
./quick-start.sh test
```

### Database Recovery
```bash
# 1. Stop services using database
docker compose stop fhir-server hl7-processor epic-connector audit-service

# 2. Backup current data (if possible)
docker compose exec postgres pg_dump -U epic_user epic_db > backup.sql

# 3. Reset database
docker compose down postgres
docker volume rm upwork1_postgres_data

# 4. Start fresh database
docker compose up -d postgres

# 5. Restore data (if backup exists)
cat backup.sql | docker compose exec -T postgres psql -U epic_user -d epic_db

# 6. Start other services
docker compose up -d
```

### Service-Specific Recovery

#### FHIR Server Recovery
```bash
# Restart with clean state
docker compose stop fhir-server
docker compose rm -f fhir-server
docker compose build fhir-server --no-cache
docker compose up -d fhir-server

# Check logs
docker compose logs fhir-server -f
```

#### API Gateway Recovery
```bash
# Clear cache and restart
docker compose exec redis redis-cli FLUSHALL
docker compose restart api-gateway
```

## Getting Help

### Log Collection for Support
```bash
# Collect all logs
mkdir epic-ehr-logs
docker compose logs > epic-ehr-logs/all-services.log
docker compose ps > epic-ehr-logs/container-status.log
docker system df > epic-ehr-logs/docker-usage.log
docker network inspect upwork1_epic-network > epic-ehr-logs/network-info.log

# Create archive
tar -czf epic-ehr-logs.tar.gz epic-ehr-logs/
```

### System Information
```bash
# System info script
echo "=== System Information ===" > system-info.txt
uname -a >> system-info.txt
docker --version >> system-info.txt
docker compose version >> system-info.txt
free -h >> system-info.txt
df -h >> system-info.txt
```

### Support Checklist

Before seeking support, ensure you have:

- [ ] Checked this troubleshooting guide
- [ ] Collected relevant logs
- [ ] Noted error messages and timestamps
- [ ] Tried basic recovery steps
- [ ] Documented steps to reproduce the issue
- [ ] System information and versions

### Emergency Contacts

For critical production issues:

1. Check system status: `./quick-start.sh status`
2. Collect logs: `docker compose logs > emergency-logs.txt`
3. Try quick recovery: `docker compose restart <failing-service>`
4. If database issues: Follow database recovery procedure
5. Document incident and timeline

Remember: Always test recovery procedures in a non-production environment first!

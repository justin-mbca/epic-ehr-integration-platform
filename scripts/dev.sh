#!/bin/bash

# EPIC EHR Integration Development Script
set -e

PROJECT_NAME="epic-ehr-integration"
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 EPIC EHR Integration Platform                ║"
    echo "║              Development Environment Manager                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    print_banner
    echo -e "${YELLOW}Usage:${NC} $0 [COMMAND]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  dev-up        Start development environment (databases only)"
    echo "  dev-down      Stop development environment"
    echo "  full-up       Start full application stack"
    echo "  full-down     Stop full application stack"
    echo "  build         Build all Docker images"
    echo "  rebuild       Rebuild all Docker images (no cache)"
    echo "  logs [service] View logs for all services or specific service"
    echo "  shell [service] Open shell in running service container"
    echo "  test          Run all tests"
    echo "  clean         Remove all containers, networks, and volumes"
    echo "  status        Show status of all services"
    echo "  health        Check health of all services"
    echo "  setup         Initial project setup"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 dev-up                    # Start PostgreSQL and Redis for development"
    echo "  $0 logs api-gateway          # View API Gateway logs"
    echo "  $0 shell hl7-processor       # Open shell in HL7 processor container"
    echo ""
}

check_dependencies() {
    command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required but not installed.${NC}" >&2; exit 1; }
    docker compose version >/dev/null 2>&1 || { echo -e "${RED}Error: Docker Compose is required but not available.${NC}" >&2; exit 1; }
}

dev_up() {
    echo -e "${GREEN}🚀 Starting development environment...${NC}"
    docker compose -f $DEV_COMPOSE_FILE up -d
    echo -e "${GREEN}✅ Development environment started!${NC}"
    echo -e "${YELLOW}📋 Services running:${NC}"
    echo "  - PostgreSQL: localhost:5433"
    echo "  - Redis: localhost:6380" 
    echo "  - PgAdmin: http://localhost:5050 (admin@epic.local / admin)"
}

dev_down() {
    echo -e "${YELLOW}🛑 Stopping development environment...${NC}"
    docker compose -f $DEV_COMPOSE_FILE down
    echo -e "${GREEN}✅ Development environment stopped!${NC}"
}

full_up() {
    echo -e "${GREEN}🚀 Starting full application stack...${NC}"
    docker compose -f $COMPOSE_FILE up -d
    echo -e "${GREEN}✅ Full application stack started!${NC}"
    echo -e "${YELLOW}📋 Services running:${NC}"
    echo "  - API Gateway: http://localhost:3000"
    echo "  - FHIR Server: http://localhost:8080"
    echo "  - HL7 Processor: http://localhost:8001"
    echo "  - EPIC Connector: http://localhost:8002"
    echo "  - Audit Service: http://localhost:8003"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
}

full_down() {
    echo -e "${YELLOW}🛑 Stopping full application stack...${NC}"
    docker compose -f $COMPOSE_FILE down
    echo -e "${GREEN}✅ Full application stack stopped!${NC}"
}

build_images() {
    echo -e "${GREEN}🔨 Building Docker images...${NC}"
    docker compose -f $COMPOSE_FILE build
    echo -e "${GREEN}✅ All images built successfully!${NC}"
}

rebuild_images() {
    echo -e "${GREEN}🔨 Rebuilding Docker images (no cache)...${NC}"
    docker compose -f $COMPOSE_FILE build --no-cache
    echo -e "${GREEN}✅ All images rebuilt successfully!${NC}"
}

show_logs() {
    if [ -z "$2" ]; then
        echo -e "${BLUE}📄 Showing logs for all services...${NC}"
        docker compose -f $COMPOSE_FILE logs -f
    else
        echo -e "${BLUE}📄 Showing logs for $2...${NC}"
        docker compose -f $COMPOSE_FILE logs -f "$2"
    fi
}

open_shell() {
    if [ -z "$2" ]; then
        echo -e "${RED}Error: Please specify a service name${NC}"
        echo "Available services: api-gateway, fhir-server, hl7-processor, epic-connector, audit-service"
        exit 1
    fi
    
    echo -e "${BLUE}🐚 Opening shell in $2...${NC}"
    docker compose -f $COMPOSE_FILE exec "$2" /bin/bash
}

run_tests() {
    echo -e "${GREEN}🧪 Running all tests...${NC}"
    # Add test commands here
    echo -e "${YELLOW}TODO: Implement test runner${NC}"
}

clean_all() {
    echo -e "${RED}🧹 Cleaning up all containers, networks, and volumes...${NC}"
    read -p "Are you sure? This will remove all data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f $COMPOSE_FILE down -v --remove-orphans
        docker compose -f $DEV_COMPOSE_FILE down -v --remove-orphans
        docker system prune -f
        echo -e "${GREEN}✅ Cleanup completed!${NC}"
    else
        echo -e "${YELLOW}Cleanup cancelled.${NC}"
    fi
}

show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    docker compose -f $COMPOSE_FILE ps
}

check_health() {
    echo -e "${BLUE}🏥 Health Check:${NC}"
    
    services=("api-gateway:3000/health" "fhir-server:8080/fhir/metadata" "hl7-processor:8001/health" "epic-connector:8002/health" "audit-service:8003/health")
    
    for service in "${services[@]}"; do
        IFS=':' read -r name endpoint <<< "$service"
        if curl -s -f "http://localhost:$endpoint" > /dev/null; then
            echo -e "  ✅ $name: ${GREEN}Healthy${NC}"
        else
            echo -e "  ❌ $name: ${RED}Unhealthy${NC}"
        fi
    done
}

initial_setup() {
    echo -e "${GREEN}🔧 Running initial project setup...${NC}"
    
    # Create necessary directories
    mkdir -p logs data certificates infrastructure/database
    
    # Set up environment files
    if [ ! -f .env ]; then
        echo "Creating .env file..."
        cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=epic_ehr
DB_USER=epic_user
DB_PASSWORD=epic_password

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
ENCRYPTION_KEY=your-encryption-key-for-phi-data-32-chars

# EPIC Configuration
EPIC_CLIENT_ID=your-epic-client-id
EPIC_CLIENT_SECRET=your-epic-client-secret
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth

# Service URLs
FHIR_SERVER_URL=http://localhost:8080
HL7_PROCESSOR_URL=http://localhost:8001
EPIC_CONNECTOR_URL=http://localhost:8002
AUDIT_SERVICE_URL=http://localhost:8003

# Logging
LOG_LEVEL=INFO
EOF
        echo -e "${GREEN}✅ .env file created${NC}"
    fi
    
    echo -e "${GREEN}✅ Initial setup completed!${NC}"
    echo -e "${YELLOW}📝 Next steps:${NC}"
    echo "  1. Update .env file with your EPIC credentials"
    echo "  2. Run '$0 dev-up' to start development environment"
    echo "  3. Run '$0 build' to build all Docker images"
    echo "  4. Run '$0 full-up' to start all services"
}

# Main execution
case "$1" in
    "dev-up")
        check_dependencies
        dev_up
        ;;
    "dev-down")
        check_dependencies
        dev_down
        ;;
    "full-up")
        check_dependencies
        full_up
        ;;
    "full-down")
        check_dependencies
        full_down
        ;;
    "build")
        check_dependencies
        build_images
        ;;
    "rebuild")
        check_dependencies
        rebuild_images
        ;;
    "logs")
        check_dependencies
        show_logs "$@"
        ;;
    "shell")
        check_dependencies
        open_shell "$@"
        ;;
    "test")
        check_dependencies
        run_tests
        ;;
    "clean")
        check_dependencies
        clean_all
        ;;
    "status")
        check_dependencies
        show_status
        ;;
    "health")
        check_dependencies
        check_health
        ;;
    "setup")
        initial_setup
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

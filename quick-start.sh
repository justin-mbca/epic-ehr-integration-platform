#!/bin/bash

# EPIC EHR Integration System - Quick Start Script
# This script helps you get the system up and running quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
}

# Function to check required ports
check_ports() {
    print_status "Checking if required ports are available..."
    
    local ports=(3000 5432 6379 8001 8002 8003 8084)
    local busy_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            busy_ports+=($port)
        fi
    done
    
    if [ ${#busy_ports[@]} -ne 0 ]; then
        print_warning "The following ports are already in use: ${busy_ports[*]}"
        print_warning "Please stop services using these ports or change the configuration."
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "All required ports are available!"
    fi
}

# Function to start services
start_services() {
    print_status "Starting EPIC EHR Integration System..."
    
    # Stop any existing containers
    print_status "Stopping any existing containers..."
    docker compose down --remove-orphans 2>/dev/null || true
    
    # Start services
    print_status "Starting all services..."
    docker compose up -d --build
    
    if [ $? -eq 0 ]; then
        print_success "Services started successfully!"
    else
        print_error "Failed to start services. Check the logs for details."
        exit 1
    fi
}

# Function to wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to become healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # Check if all services are running
        local running_services=$(docker compose ps --services --filter "status=running" | wc -l)
        local total_services=$(docker compose ps --services | wc -l)
        
        if [ "$running_services" -eq "$total_services" ]; then
            print_success "All services are running!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Services did not start within expected time. Check logs with: docker compose logs"
            exit 1
        fi
        
        print_status "Attempt $attempt/$max_attempts - Waiting for services to start..."
        sleep 10
    done
}

# Function to test endpoints
test_endpoints() {
    print_status "Testing service endpoints..."
    
    # Test API Gateway
    if curl -s http://localhost:3000/health > /dev/null; then
        print_success "✓ API Gateway (http://localhost:3000) is responding"
    else
        print_warning "✗ API Gateway health check failed"
    fi
    
    # Test FHIR Server
    if curl -s -u admin:admin123 http://localhost:8084/fhir/health > /dev/null; then
        print_success "✓ FHIR Server (http://localhost:8084) is responding"
    else
        print_warning "✗ FHIR Server health check failed"
    fi
    
    # Test HL7 Processor
    if curl -s http://localhost:8001/health > /dev/null; then
        print_success "✓ HL7 Processor (http://localhost:8001) is responding"
    else
        print_warning "✗ HL7 Processor health check failed"
    fi
    
    # Test EPIC Connector
    if curl -s http://localhost:8002/health > /dev/null; then
        print_success "✓ EPIC Connector (http://localhost:8002) is responding"
    else
        print_warning "✗ EPIC Connector health check failed"
    fi
    
    # Test Audit Service
    if curl -s http://localhost:8003/health > /dev/null; then
        print_success "✓ Audit Service (http://localhost:8003) is responding"
    else
        print_warning "✗ Audit Service health check failed"
    fi
}

# Function to display system status
show_status() {
    print_status "System Status:"
    echo
    docker compose ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"
    echo
}

# Function to show usage examples
show_usage_examples() {
    cat << EOF

${GREEN}🎉 EPIC EHR Integration System is now running!${NC}

${BLUE}📋 Quick Usage Examples:${NC}

${YELLOW}1. Get OAuth2 Token:${NC}
curl -X POST http://localhost:3000/oauth/token \\
  -H "Content-Type: application/json" \\
  -d '{
    "grant_type": "client_credentials",
    "client_id": "epic-test-client",
    "client_secret": "test-secret"
  }'

${YELLOW}2. Access FHIR Resources (Direct):${NC}
curl -u admin:admin123 http://localhost:8084/fhir/Patient

${YELLOW}3. Get FHIR Metadata:${NC}
curl -u admin:admin123 http://localhost:8084/fhir/metadata

${YELLOW}4. Get Specific Patient:${NC}
curl -u admin:admin123 http://localhost:8084/fhir/Patient/1

${YELLOW}5. Check Service Health:${NC}
curl http://localhost:3000/health
curl -u admin:admin123 http://localhost:8084/actuator/health

${BLUE}📚 Documentation:${NC}
- Main README: ./README.md
- API Gateway: ./docs/API_GATEWAY.md
- FHIR Server: ./docs/FHIR_SERVER.md
- Deployment Guide: ./docs/DEPLOYMENT.md

${BLUE}🔧 Management Commands:${NC}
- View logs: docker compose logs -f
- Stop system: docker compose down
- Restart service: docker compose restart <service-name>
- View containers: docker compose ps

${BLUE}🌐 Service URLs:${NC}
- API Gateway: http://localhost:3000
- FHIR Server: http://localhost:8084
- HL7 Processor: http://localhost:8001
- EPIC Connector: http://localhost:8002
- Audit Service: http://localhost:8003
- PostgreSQL: localhost:5432
- Redis: localhost:6379

${BLUE}🔐 Default Credentials:${NC}
- FHIR Server: admin / admin123
- Database: epic_user / epic_password
- OAuth2 Test Client: epic-test-client / test-secret

${RED}⚠️  Security Notice:${NC} Change default credentials before production use!

EOF
}

# Function to show menu
show_menu() {
    cat << EOF

${BLUE}EPIC EHR Integration System - Quick Start${NC}

Please select an option:

1) Start the system (full deployment)
2) Check system status
3) Stop the system
4) View logs
5) Test endpoints
6) Show usage examples
7) Exit

EOF
}

# Function to handle menu selection
handle_menu() {
    while true; do
        show_menu
        read -p "Enter your choice (1-7): " choice
        
        case $choice in
            1)
                check_prerequisites
                check_ports
                start_services
                wait_for_services
                sleep 5  # Additional wait for health checks
                test_endpoints
                show_status
                show_usage_examples
                ;;
            2)
                show_status
                ;;
            3)
                print_status "Stopping the system..."
                docker compose down
                print_success "System stopped!"
                ;;
            4)
                print_status "Showing logs (Ctrl+C to exit)..."
                docker compose logs -f
                ;;
            5)
                test_endpoints
                ;;
            6)
                show_usage_examples
                ;;
            7)
                print_success "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please choose 1-7."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Main execution
main() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   EPIC EHR Integration System - Quick Start                 ║
║   Healthcare Interoperability Platform                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Check if running with arguments
    if [ $# -eq 0 ]; then
        handle_menu
    else
        case $1 in
            start|up)
                check_prerequisites
                check_ports
                start_services
                wait_for_services
                sleep 5
                test_endpoints
                show_status
                show_usage_examples
                ;;
            stop|down)
                print_status "Stopping the system..."
                docker compose down
                print_success "System stopped!"
                ;;
            status)
                show_status
                ;;
            test)
                test_endpoints
                ;;
            logs)
                docker compose logs -f
                ;;
            examples)
                show_usage_examples
                ;;
            *)
                echo "Usage: $0 [start|stop|status|test|logs|examples]"
                echo "Run without arguments for interactive menu."
                exit 1
                ;;
        esac
    fi
}

# Run main function with all arguments
main "$@"

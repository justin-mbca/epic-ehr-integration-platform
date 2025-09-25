#!/bin/bash

# EPIC EHR Integration - Python Environment Setup Script
# This script sets up Python virtual environments for all Python-based services

set -e

echo "🐍 Setting up Python environments for EPIC EHR Integration..."

# Check if Python 3.9+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Function to setup virtual environment for a service
setup_venv() {
    local service_name=$1
    local service_path="services/$service_name"
    
    echo "🔧 Setting up virtual environment for $service_name..."
    
    cd "$service_path"
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements if they exist
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "✅ Installed requirements for $service_name"
    fi
    
    # Deactivate and return to root
    deactivate
    cd ../..
    
    echo "✅ Virtual environment created for $service_name"
}

# Setup virtual environments for Python services
echo "📦 Creating virtual environments..."

setup_venv "hl7-processor"
setup_venv "epic-connector" 
setup_venv "audit-service"

echo ""
echo "🎉 Python environments setup complete!"
echo ""
echo "To activate a virtual environment:"
echo "  cd services/<service-name>"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""
echo "Services with Python environments:"
echo "  • hl7-processor"
echo "  • epic-connector"
echo "  • audit-service"

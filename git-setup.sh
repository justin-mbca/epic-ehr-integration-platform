#!/bin/bash

# Git Setup and Push Script for EPIC EHR Integration Platform
# Run this script to initialize git and push to GitHub repository

set -e

echo "🚀 Setting up Git repository for EPIC EHR Integration Platform"
echo "Repository: https://github.com/justin-mbca/epic-ehr-integration-platform"
echo ""

# Check if we're already in a git repository
if [ -d ".git" ]; then
    echo "📁 Git repository already exists. Checking remote..."
    
    # Check if the correct remote exists
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [ "$REMOTE_URL" != "https://github.com/justin-mbca/epic-ehr-integration-platform.git" ]; then
        echo "🔄 Setting correct remote origin..."
        git remote set-url origin https://github.com/justin-mbca/epic-ehr-integration-platform.git
    else
        echo "✅ Correct remote origin already set"
    fi
else
    echo "🔧 Initializing new Git repository..."
    git init
    git remote add origin https://github.com/justin-mbca/epic-ehr-integration-platform.git
fi

echo ""
echo "📋 Checking git status..."
git status

echo ""
echo "➕ Adding all files to git..."
git add .

echo ""
echo "💾 Creating commit..."
git commit -m "Initial commit: Complete EPIC EHR Integration Platform

Features:
✅ FHIR R4 Server with HAPI FHIR 6.6.0
✅ OAuth2 API Gateway with JWT authentication  
✅ HL7 Message Processing service
✅ EPIC Connector for EHR integration
✅ Audit Service for compliance logging
✅ PostgreSQL and Redis data layers
✅ Docker Compose orchestration
✅ Comprehensive documentation
✅ Interactive quick-start script
✅ Health monitoring and diagnostics

Architecture:
- Microservices design with Docker containers
- Spring Boot 3.1 for FHIR server
- Node.js Express for API Gateway
- Python FastAPI for processing services
- HIPAA-compliant security design
- Production-ready deployment guides"

echo ""
echo "📤 Pushing to GitHub repository..."
git branch -M main
git push -u origin main

echo ""
echo "🎉 Successfully pushed to GitHub!"
echo "🌐 Repository URL: https://github.com/justin-mbca/epic-ehr-integration-platform"
echo ""
echo "Next steps:"
echo "1. Visit the GitHub repository to verify the upload"
echo "2. Update repository description and topics on GitHub"
echo "3. Consider adding a license file"
echo "4. Set up branch protection rules if needed"

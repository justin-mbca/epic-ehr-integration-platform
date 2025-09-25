# EPIC EHR Integration Project - Copilot Instructions

This project implements a comprehensive EPIC EHR integration system with HL7, FHIR, and Connection Hub capabilities.

## Project Overview
- **Purpose**: Healthcare interoperability system for EPIC EHR integration
- **Architecture**: Microservices-based with Docker/Kubernetes deployment
- **Standards**: HL7 v2/v3, FHIR R4, SMART on FHIR
- **Compliance**: HIPAA, PHIPA, and healthcare regulations

## Key Components
- API Gateway for routing and authentication
- HL7 Message Broker (Mirth Connect compatible)
- FHIR Resource Server (HAPI FHIR)
- EPIC Connection Hub integration
- Security and audit services
- DevOps pipeline and monitoring

## Development Guidelines
- Follow healthcare interoperability standards
- Implement robust error handling and logging
- Ensure data encryption and access controls
- Use containerized microservices architecture
- Maintain comprehensive documentation
- Include security scanning and compliance checks

## Technologies Used
- **Backend**: Node.js, Python, Java Spring Boot
- **Messaging**: Apache Kafka, Mirth Connect
- **FHIR**: HAPI FHIR Server
- **Database**: PostgreSQL, MongoDB
- **DevOps**: Docker, Kubernetes, Jenkins, Terraform
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **Security**: OAuth2.0, JWT, Vault

## Compliance Requirements
- All PHI must be encrypted in transit and at rest
- Implement audit logging for all data access
- Follow HIPAA minimum necessary principle
- Ensure secure authentication and authorization
- Regular security assessments and penetration testing

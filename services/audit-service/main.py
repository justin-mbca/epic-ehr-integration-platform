"""
Audit Service
HIPAA-compliant audit logging and compliance monitoring for EPIC EHR integration
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import structlog
import jwt
from typing import Optional, Dict, Any, List
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid
import hashlib
from cryptography.fernet import Fernet
import pandas as pd

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Audit Service",
    description="HIPAA-compliant audit logging and compliance monitoring",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/epic_audit_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Encryption setup
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if ENCRYPTION_KEY:
    cipher_suite = Fernet(ENCRYPTION_KEY)
else:
    # Generate a new key if none provided
    cipher_suite = Fernet(Fernet.generate_key())

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(String(255), nullable=False)
    user_role = Column(String(100))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    patient_id = Column(String(255))  # For patient-related actions
    source_ip = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(255))
    outcome = Column(String(50), nullable=False)  # SUCCESS, FAILURE, WARNING
    details = Column(Text)  # Encrypted details
    compliance_flags = Column(Text)  # JSON string of compliance-related flags
    retention_until = Column(DateTime)  # For automatic purging
    
class ComplianceReport(Base):
    __tablename__ = "compliance_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(255), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    summary = Column(Text)
    details = Column(Text)  # Encrypted report data
    file_path = Column(String(500))  # Path to generated report file

class AccessAttempt(Base):
    __tablename__ = "access_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(255))
    source_ip = Column(String(45), nullable=False)
    user_agent = Column(Text)
    attempted_resource = Column(String(500))
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255))
    risk_score = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class AuditLogEntry(BaseModel):
    user_id: str = Field(..., description="User identifier")
    user_role: Optional[str] = Field(None, description="User role/permission level")
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Type of resource accessed")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    patient_id: Optional[str] = Field(None, description="Patient ID (for PHI access)")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    session_id: Optional[str] = Field(None, description="Session identifier")
    outcome: str = Field(..., description="SUCCESS, FAILURE, or WARNING")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class AuditQuery(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Start date for query")
    end_date: Optional[datetime] = Field(None, description="End date for query")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    outcome: Optional[str] = Field(None, description="Filter by outcome")
    limit: int = Field(100, description="Maximum number of results")

class ComplianceReportRequest(BaseModel):
    report_type: str = Field(..., description="Type of compliance report")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    include_details: bool = Field(True, description="Include detailed breakdown")

class SecurityAlert(BaseModel):
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    affected_resources: List[str]
    recommended_actions: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            os.getenv("JWT_SECRET", "fallback-secret"), 
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Utility functions
def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data for storage"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def calculate_risk_score(user_id: str, source_ip: str, action: str) -> int:
    """Calculate risk score for security monitoring"""
    score = 0
    
    # Add risk factors
    if action in ["DELETE", "EXPORT", "BULK_ACCESS"]:
        score += 30
    
    # Check for unusual access patterns (simplified)
    if "admin" in action.lower():
        score += 20
    
    # IP-based risk (simplified - in production, use threat intelligence)
    private_ips = ["192.168.", "10.", "172.16.", "127.0.0.1"]
    if not any(source_ip.startswith(ip) for ip in private_ips):
        score += 10
    
    return min(score, 100)  # Cap at 100

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "audit-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/audit/log")
async def create_audit_log(
    audit_entry: AuditLogEntry,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(verify_token)
):
    """Create new audit log entry"""
    try:
        # Encrypt sensitive details
        encrypted_details = None
        if audit_entry.details:
            encrypted_details = encrypt_sensitive_data(str(audit_entry.details))
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=audit_entry.user_id,
            user_role=audit_entry.user_role,
            action=audit_entry.action,
            resource_type=audit_entry.resource_type,
            resource_id=audit_entry.resource_id,
            patient_id=audit_entry.patient_id,
            source_ip=audit_entry.source_ip,
            user_agent=audit_entry.user_agent,
            session_id=audit_entry.session_id,
            outcome=audit_entry.outcome,
            details=encrypted_details,
            retention_until=datetime.utcnow() + timedelta(days=2555)  # 7 years HIPAA retention
        )
        
        db.add(audit_log)
        db.commit()
        
        # Background security monitoring
        background_tasks.add_task(
            monitor_security_patterns, 
            audit_entry.user_id, 
            audit_entry.source_ip, 
            audit_entry.action
        )
        
        logger.info("Audit log entry created", 
                   audit_id=str(audit_log.id),
                   user_id=audit_entry.user_id,
                   action=audit_entry.action)
        
        return {
            "success": True,
            "audit_id": str(audit_log.id),
            "message": "Audit log entry created"
        }
        
    except Exception as e:
        logger.error("Failed to create audit log", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create audit log")

@app.post("/audit/query")
async def query_audit_logs(
    query: AuditQuery,
    db: Session = Depends(get_db),
    user = Depends(verify_token)
):
    """Query audit logs with filters"""
    try:
        # Build query
        db_query = db.query(AuditLog)
        
        if query.start_date:
            db_query = db_query.filter(AuditLog.timestamp >= query.start_date)
        if query.end_date:
            db_query = db_query.filter(AuditLog.timestamp <= query.end_date)
        if query.user_id:
            db_query = db_query.filter(AuditLog.user_id == query.user_id)
        if query.action:
            db_query = db_query.filter(AuditLog.action == query.action)
        if query.patient_id:
            db_query = db_query.filter(AuditLog.patient_id == query.patient_id)
        if query.outcome:
            db_query = db_query.filter(AuditLog.outcome == query.outcome)
        
        # Execute query with limit
        results = db_query.order_by(AuditLog.timestamp.desc()).limit(query.limit).all()
        
        # Format results (decrypt details if needed)
        formatted_results = []
        for result in results:
            entry = {
                "id": str(result.id),
                "timestamp": result.timestamp.isoformat(),
                "user_id": result.user_id,
                "user_role": result.user_role,
                "action": result.action,
                "resource_type": result.resource_type,
                "resource_id": result.resource_id,
                "patient_id": result.patient_id,
                "source_ip": result.source_ip,
                "outcome": result.outcome
            }
            
            # Only include decrypted details for authorized users
            if user.get("scope", "").includes("audit:read_details"):
                if result.details:
                    try:
                        entry["details"] = decrypt_sensitive_data(result.details)
                    except:
                        entry["details"] = "[ENCRYPTED]"
            
            formatted_results.append(entry)
        
        logger.info("Audit query executed", 
                   query_user=user.get("client_id"),
                   results_count=len(formatted_results))
        
        return {
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results)
        }
        
    except Exception as e:
        logger.error("Audit query failed", error=str(e))
        raise HTTPException(status_code=500, detail="Query failed")

@app.post("/compliance/report")
async def generate_compliance_report(
    report_request: ComplianceReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(verify_token)
):
    """Generate compliance report"""
    try:
        # Create report record
        report = ComplianceReport(
            report_type=report_request.report_type,
            generated_by=user.get("client_id", "unknown"),
            period_start=report_request.period_start,
            period_end=report_request.period_end
        )
        
        db.add(report)
        db.commit()
        
        # Generate report in background
        background_tasks.add_task(
            generate_report_data,
            str(report.id),
            report_request
        )
        
        logger.info("Compliance report generation initiated", 
                   report_id=str(report.id),
                   report_type=report_request.report_type)
        
        return {
            "success": True,
            "report_id": str(report.id),
            "message": "Compliance report generation started",
            "estimated_completion": "5-10 minutes"
        }
        
    except Exception as e:
        logger.error("Failed to initiate compliance report", error=str(e))
        raise HTTPException(status_code=500, detail="Report generation failed")

@app.get("/security/alerts")
async def get_security_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, description="Maximum alerts to return"),
    user = Depends(verify_token)
):
    """Get security alerts and anomalies"""
    try:
        # In production, this would query a security monitoring system
        # For now, return sample alerts based on recent access patterns
        
        alerts = await analyze_security_patterns(severity, limit)
        
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error("Failed to retrieve security alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

# Background tasks
async def monitor_security_patterns(user_id: str, source_ip: str, action: str):
    """Monitor for suspicious security patterns"""
    try:
        risk_score = calculate_risk_score(user_id, source_ip, action)
        
        # Store access attempt
        db = SessionLocal()
        access_attempt = AccessAttempt(
            user_id=user_id,
            source_ip=source_ip,
            attempted_resource=action,
            success=True,  # If we're here, access was granted
            risk_score=risk_score
        )
        db.add(access_attempt)
        db.commit()
        db.close()
        
        # Generate alert if high risk
        if risk_score > 70:
            logger.warning("High-risk access detected", 
                         user_id=user_id,
                         source_ip=source_ip,
                         action=action,
                         risk_score=risk_score)
            
            # In production, send alert to security team
            
    except Exception as e:
        logger.error("Security monitoring failed", error=str(e))

async def generate_report_data(report_id: str, report_request: ComplianceReportRequest):
    """Generate detailed compliance report data"""
    try:
        db = SessionLocal()
        
        # Query audit data for report period
        audit_data = db.query(AuditLog).filter(
            AuditLog.timestamp >= report_request.period_start,
            AuditLog.timestamp <= report_request.period_end
        ).all()
        
        # Generate report summary
        summary = {
            "total_actions": len(audit_data),
            "unique_users": len(set(entry.user_id for entry in audit_data)),
            "failed_attempts": len([entry for entry in audit_data if entry.outcome == "FAILURE"]),
            "patient_record_accesses": len([entry for entry in audit_data if entry.patient_id])
        }
        
        # Update report record
        report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
        if report:
            report.summary = str(summary)
            report.details = encrypt_sensitive_data(str(audit_data))
            db.commit()
        
        db.close()
        
        logger.info("Compliance report generated", report_id=report_id)
        
    except Exception as e:
        logger.error("Report generation failed", report_id=report_id, error=str(e))

async def analyze_security_patterns(severity_filter: Optional[str], limit: int) -> List[SecurityAlert]:
    """Analyze access patterns for security anomalies"""
    # This is a simplified implementation
    # In production, use advanced analytics and ML
    
    alerts = []
    
    # Sample alerts based on common security concerns
    sample_alerts = [
        SecurityAlert(
            alert_type="UNUSUAL_ACCESS_PATTERN",
            severity="MEDIUM",
            description="User accessing unusual number of patient records",
            affected_resources=["Patient/12345", "Patient/67890"],
            recommended_actions=["Review user access patterns", "Verify business justification"]
        ),
        SecurityAlert(
            alert_type="FAILED_LOGIN_ATTEMPTS",
            severity="HIGH",
            description="Multiple failed authentication attempts from same IP",
            affected_resources=["Auth endpoint"],
            recommended_actions=["Block IP address", "Investigate source"]
        )
    ]
    
    # Filter by severity if specified
    if severity_filter:
        alerts = [alert for alert in sample_alerts if alert.severity == severity_filter.upper()]
    else:
        alerts = sample_alerts
    
    return alerts[:limit]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

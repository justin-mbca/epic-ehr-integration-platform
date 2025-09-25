"""
HL7 Processor Service
Healthcare message processing for EPIC EHR integration
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import hl7
# Using python-hl7 library for simpler HL7 processing
import structlog
import httpx
import jwt
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
import asyncio

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="HL7 Processor Service",
    description="Healthcare message processing for EPIC EHR integration",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class HL7Message(BaseModel):
    message_type: str = Field(..., description="HL7 message type (e.g., ADT^A01)")
    content: str = Field(..., description="Raw HL7 message content")
    source_system: Optional[str] = Field(None, description="Source system identifier")
    destination_system: Optional[str] = Field(None, description="Destination system")
    message_id: Optional[str] = Field(None, description="Unique message identifier")

class ProcessedMessage(BaseModel):
    message_id: str
    message_type: str
    status: str
    parsed_data: Dict[str, Any]
    processing_time: datetime
    errors: Optional[List[str]] = None

class HL7ProcessingResponse(BaseModel):
    success: bool
    message_id: str
    status: str
    message: str
    processed_data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

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

# HL7 Processing Functions
class HL7Processor:
    def __init__(self):
        self.supported_message_types = [
            "ADT^A01",  # Admit/Visit Notification
            "ADT^A08",  # Update Patient Information
            "ORM^O01",  # Order Message
            "ORU^R01",  # Observation Result
            "SIU^S12",  # New Appointment Booking
            "DFT^P03",  # Post Detail Financial Transaction
        ]
    
    async def parse_hl7_message(self, raw_message: str) -> Dict[str, Any]:
        """Parse HL7 message and extract key information"""
        try:
            # Clean and prepare message
            cleaned_message = raw_message.replace('\n', '\r').strip()
            
            # Parse using hl7apy
            # Parse HL7 message using python-hl7
            parsed_msg = hl7.parse(cleaned_message)
            
            # Extract common segments
            result = {
                "message_header": self._extract_msh_segment(parsed_msg),
                "patient_info": self._extract_patient_info(parsed_msg),
                "event_info": self._extract_event_info(parsed_msg),
                "raw_segments": []
            }
            
            # Extract all segments
            for segment in parsed_msg.children:
                segment_data = {
                    "segment_type": segment.name,
                    "fields": []
                }
                
                for field in segment.children:
                    if field.value:
                        segment_data["fields"].append({
                            "field_name": field.name,
                            "value": str(field.value)
                        })
                
                result["raw_segments"].append(segment_data)
            
            return result
            
        except Exception as e:
            logger.error("HL7 parsing error", error=str(e), message_preview=raw_message[:100])
            raise ValueError(f"Failed to parse HL7 message: {str(e)}")
    
    def _extract_msh_segment(self, parsed_msg) -> Dict[str, Any]:
        """Extract MSH (Message Header) segment information"""
        try:
            msh = parsed_msg.segment('MSH')
            return {
                "sending_application": str(msh[3]) if len(msh) > 3 else None,
                "sending_facility": str(msh[4]) if len(msh) > 4 else None,
                "receiving_application": str(msh[5]) if len(msh) > 5 else None,
                "receiving_facility": str(msh[6]) if len(msh) > 6 else None,
                "timestamp": str(msh[7]) if len(msh) > 7 else None,
                "message_type": str(msh[9]) if len(msh) > 9 else None,
                "message_control_id": str(msh[10]) if len(msh) > 10 else None,
                "processing_id": str(msh[11]) if len(msh) > 11 else None,
                "version_id": str(msh[12]) if len(msh) > 12 else None,
            }
        except (AttributeError, IndexError):
            return {}
    
    def _extract_patient_info(self, parsed_msg) -> Dict[str, Any]:
        """Extract patient information from PID segment"""
        try:
            pid = parsed_msg.segment('PID')
            return {
                "patient_id": str(pid[3]) if len(pid) > 3 else None,
                "patient_name": str(pid[5]) if len(pid) > 5 else None,
                "date_of_birth": str(pid[7]) if len(pid) > 7 else None,
                "gender": str(pid[8]) if len(pid) > 8 else None,
                "patient_address": str(pid[11]) if len(pid) > 11 else None,
            }
        except (AttributeError, IndexError):
            return {}
    
    def _extract_event_info(self, parsed_msg) -> Dict[str, Any]:
        """Extract event information from EVN segment"""
        try:
            evn = parsed_msg.segment('EVN')
            return {
                "event_type": str(evn[1]) if len(evn) > 1 else None,
                "recorded_datetime": str(evn[2]) if len(evn) > 2 else None,
                "planned_event_datetime": str(evn[3]) if len(evn) > 3 else None,
                "event_reason": str(evn[4]) if len(evn) > 4 else None,
            }
        except (AttributeError, IndexError):
            return {}
    
    async def validate_message(self, message_type: str, parsed_data: Dict[str, Any]) -> List[str]:
        """Validate HL7 message structure and required fields"""
        errors = []
        
        # Check if message type is supported
        if message_type not in self.supported_message_types:
            errors.append(f"Unsupported message type: {message_type}")
        
        # Validate required MSH fields
        msh = parsed_data.get("message_header", {})
        required_msh_fields = ["sending_application", "message_type", "message_control_id"]
        
        for field in required_msh_fields:
            if not msh.get(field):
                errors.append(f"Missing required MSH field: {field}")
        
        # Additional validations based on message type
        if message_type.startswith("ADT"):
            patient_info = parsed_data.get("patient_info", {})
            if not patient_info.get("patient_id"):
                errors.append("Patient ID is required for ADT messages")
        
        return errors

# Initialize processor
processor = HL7Processor()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hl7-processor",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/process", response_model=HL7ProcessingResponse)
async def process_hl7_message(
    message: HL7Message,
    background_tasks: BackgroundTasks,
    user = Depends(verify_token)
):
    """Process an HL7 message"""
    message_id = message.message_id or f"msg_{int(datetime.utcnow().timestamp())}"
    
    logger.info("Processing HL7 message", 
               message_id=message_id, 
               message_type=message.message_type,
               user_id=user.get("client_id"))
    
    try:
        # Parse the message
        parsed_data = await processor.parse_hl7_message(message.content)
        
        # Validate the message
        validation_errors = await processor.validate_message(message.message_type, parsed_data)
        
        if validation_errors:
            logger.warning("HL7 message validation failed", 
                         message_id=message_id, 
                         errors=validation_errors)
            return HL7ProcessingResponse(
                success=False,
                message_id=message_id,
                status="validation_failed",
                message="Message validation failed",
                errors=validation_errors
            )
        
        # Queue for further processing
        background_tasks.add_task(forward_to_fhir, parsed_data, message_id)
        
        logger.info("HL7 message processed successfully", message_id=message_id)
        
        return HL7ProcessingResponse(
            success=True,
            message_id=message_id,
            status="processed",
            message="Message processed successfully",
            processed_data=parsed_data
        )
        
    except ValueError as e:
        logger.error("HL7 processing error", message_id=message_id, error=str(e))
        return HL7ProcessingResponse(
            success=False,
            message_id=message_id,
            status="parsing_failed",
            message=str(e),
            errors=[str(e)]
        )
    except Exception as e:
        logger.error("Unexpected error processing HL7 message", 
                    message_id=message_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal processing error")

@app.get("/supported-types")
async def get_supported_message_types(user = Depends(verify_token)):
    """Get list of supported HL7 message types"""
    return {
        "supported_types": processor.supported_message_types,
        "count": len(processor.supported_message_types)
    }

# Background task functions
async def forward_to_fhir(parsed_data: Dict[str, Any], message_id: str):
    """Forward processed HL7 data to FHIR server"""
    try:
        fhir_server_url = os.getenv("FHIR_SERVER_URL", "http://localhost:8080")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{fhir_server_url}/fhir/Bundle",
                json=parsed_data,
                headers={"Content-Type": "application/fhir+json"}
            )
            
            if response.status_code == 201:
                logger.info("Successfully forwarded to FHIR server", message_id=message_id)
            else:
                logger.error("Failed to forward to FHIR server", 
                           message_id=message_id, 
                           status_code=response.status_code)
                
    except Exception as e:
        logger.error("Error forwarding to FHIR server", 
                    message_id=message_id, 
                    error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

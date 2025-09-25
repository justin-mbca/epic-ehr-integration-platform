"""
EPIC Connector Service
Handles integration with EPIC EHR systems via Connection Hub and SMART on FHIR
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, HttpUrl
import structlog
import httpx
import jwt
from typing import Optional, Dict, Any, List
import os
from datetime import datetime, timedelta
import asyncio
from authlib.integrations.httpx_client import AsyncOAuth2Client
import json

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
    title="EPIC Connector Service",
    description="Integration service for EPIC EHR systems",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class EPICConnectionConfig(BaseModel):
    client_id: str = Field(..., description="EPIC client ID")
    client_secret: str = Field(..., description="EPIC client secret")
    base_url: HttpUrl = Field(..., description="EPIC base URL")
    sandbox_mode: bool = Field(default=True, description="Use sandbox environment")

class FHIRQuery(BaseModel):
    resource_type: str = Field(..., description="FHIR resource type (Patient, Observation, etc.)")
    patient_id: Optional[str] = Field(None, description="Patient identifier")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")
    additional_params: Optional[Dict[str, Any]] = Field(None, description="Additional query parameters")

class EPICResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    epic_response_code: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PatientSearchRequest(BaseModel):
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    birthdate: Optional[str] = None
    identifier: Optional[str] = None
    gender: Optional[str] = None

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

# EPIC Integration Class
class EPICConnector:
    def __init__(self):
        self.client_id = os.getenv("EPIC_CLIENT_ID")
        self.client_secret = os.getenv("EPIC_CLIENT_SECRET")
        self.base_url = os.getenv("EPIC_BASE_URL", "https://fhir.epic.com/interconnect-fhir-oauth")
        self.sandbox_url = os.getenv("EPIC_SANDBOX_URL", "https://fhir.epic.com/interconnect-fhir-oauth")
        self.access_token = None
        self.token_expires_at = None
        
    async def get_access_token(self, sandbox_mode: bool = True) -> str:
        """Get OAuth2 access token from EPIC"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
            
        try:
            base_url = self.sandbox_url if sandbox_mode else self.base_url
            token_url = f"{base_url}/oauth2/token"
            
            async with AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret
            ) as client:
                
                token_response = await client.fetch_token(
                    token_url,
                    grant_type="client_credentials"
                )
                
                self.access_token = token_response["access_token"]
                expires_in = token_response.get("expires_in", 3600)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                
                logger.info("EPIC access token obtained", expires_in=expires_in)
                return self.access_token
                
        except Exception as e:
            logger.error("Failed to obtain EPIC access token", error=str(e))
            raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
    
    async def make_fhir_request(self, endpoint: str, method: str = "GET", 
                               data: Optional[Dict] = None, 
                               sandbox_mode: bool = True) -> Dict[str, Any]:
        """Make authenticated FHIR request to EPIC"""
        try:
            token = await self.get_access_token(sandbox_mode)
            base_url = self.sandbox_url if sandbox_mode else self.base_url
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                logger.info("EPIC FHIR request completed", 
                           url=url, 
                           method=method,
                           status_code=response.status_code)
                
                if response.status_code >= 400:
                    error_detail = response.text
                    logger.error("EPIC FHIR request failed", 
                               status_code=response.status_code,
                               error=error_detail)
                    return {
                        "error": error_detail,
                        "status_code": response.status_code
                    }
                
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("EPIC FHIR request timeout", endpoint=endpoint)
            raise HTTPException(status_code=504, detail="Request to EPIC timed out")
        except Exception as e:
            logger.error("EPIC FHIR request error", endpoint=endpoint, error=str(e))
            raise HTTPException(status_code=500, detail=f"EPIC request failed: {str(e)}")
    
    async def search_patients(self, search_params: PatientSearchRequest, 
                            sandbox_mode: bool = True) -> Dict[str, Any]:
        """Search for patients in EPIC"""
        query_params = []
        
        if search_params.family_name:
            query_params.append(f"family={search_params.family_name}")
        if search_params.given_name:
            query_params.append(f"given={search_params.given_name}")
        if search_params.birthdate:
            query_params.append(f"birthdate={search_params.birthdate}")
        if search_params.identifier:
            query_params.append(f"identifier={search_params.identifier}")
        if search_params.gender:
            query_params.append(f"gender={search_params.gender}")
        
        endpoint = f"Patient?{'&'.join(query_params)}" if query_params else "Patient"
        
        return await self.make_fhir_request(endpoint, sandbox_mode=sandbox_mode)
    
    async def get_patient_data(self, patient_id: str, 
                              resource_types: List[str] = None,
                              sandbox_mode: bool = True) -> Dict[str, Any]:
        """Get comprehensive patient data from EPIC"""
        if resource_types is None:
            resource_types = ["Patient", "Observation", "Condition", "MedicationRequest", "Encounter"]
        
        results = {}
        
        for resource_type in resource_types:
            try:
                if resource_type == "Patient":
                    endpoint = f"Patient/{patient_id}"
                else:
                    endpoint = f"{resource_type}?patient={patient_id}"
                
                data = await self.make_fhir_request(endpoint, sandbox_mode=sandbox_mode)
                results[resource_type] = data
                
            except Exception as e:
                logger.warning(f"Failed to fetch {resource_type} for patient {patient_id}", 
                             error=str(e))
                results[resource_type] = {"error": str(e)}
        
        return results

# Initialize connector
epic_connector = EPICConnector()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "epic-connector",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/authenticate", response_model=EPICResponse)
async def authenticate_with_epic(
    config: Optional[EPICConnectionConfig] = None,
    user = Depends(verify_token)
):
    """Test authentication with EPIC"""
    try:
        sandbox_mode = config.sandbox_mode if config else True
        
        if config:
            # Temporarily update configuration
            epic_connector.client_id = config.client_id
            epic_connector.client_secret = config.client_secret
            epic_connector.base_url = str(config.base_url)
        
        token = await epic_connector.get_access_token(sandbox_mode)
        
        return EPICResponse(
            success=True,
            data={"message": "Authentication successful", "has_token": bool(token)}
        )
        
    except Exception as e:
        return EPICResponse(
            success=False,
            error=str(e)
        )

@app.post("/patients/search", response_model=EPICResponse)
async def search_patients(
    search_request: PatientSearchRequest,
    sandbox_mode: bool = True,
    user = Depends(verify_token)
):
    """Search for patients in EPIC"""
    try:
        logger.info("Searching patients in EPIC", 
                   search_params=search_request.dict(exclude_unset=True),
                   user_id=user.get("client_id"))
        
        results = await epic_connector.search_patients(search_request, sandbox_mode)
        
        return EPICResponse(
            success=True,
            data=results
        )
        
    except Exception as e:
        logger.error("Patient search failed", error=str(e))
        return EPICResponse(
            success=False,
            error=str(e)
        )

@app.get("/patients/{patient_id}", response_model=EPICResponse)
async def get_patient(
    patient_id: str,
    resource_types: Optional[str] = None,
    sandbox_mode: bool = True,
    user = Depends(verify_token)
):
    """Get patient data from EPIC"""
    try:
        logger.info("Fetching patient data from EPIC", 
                   patient_id=patient_id,
                   user_id=user.get("client_id"))
        
        if resource_types:
            resource_list = [r.strip() for r in resource_types.split(",")]
        else:
            resource_list = None
        
        results = await epic_connector.get_patient_data(
            patient_id, 
            resource_list, 
            sandbox_mode
        )
        
        return EPICResponse(
            success=True,
            data=results
        )
        
    except Exception as e:
        logger.error("Failed to fetch patient data", 
                    patient_id=patient_id, 
                    error=str(e))
        return EPICResponse(
            success=False,
            error=str(e)
        )

@app.post("/fhir/query", response_model=EPICResponse)
async def execute_fhir_query(
    query: FHIRQuery,
    sandbox_mode: bool = True,
    user = Depends(verify_token)
):
    """Execute custom FHIR query against EPIC"""
    try:
        logger.info("Executing FHIR query", 
                   resource_type=query.resource_type,
                   user_id=user.get("client_id"))
        
        # Build query parameters
        params = []
        
        if query.patient_id:
            params.append(f"patient={query.patient_id}")
        
        if query.date_range:
            for key, value in query.date_range.items():
                params.append(f"{key}={value}")
        
        if query.additional_params:
            for key, value in query.additional_params.items():
                params.append(f"{key}={value}")
        
        endpoint = f"{query.resource_type}?{'&'.join(params)}" if params else query.resource_type
        
        results = await epic_connector.make_fhir_request(endpoint, sandbox_mode=sandbox_mode)
        
        return EPICResponse(
            success=True,
            data=results
        )
        
    except Exception as e:
        logger.error("FHIR query failed", error=str(e))
        return EPICResponse(
            success=False,
            error=str(e)
        )

@app.get("/metadata")
async def get_epic_metadata(
    sandbox_mode: bool = True,
    user = Depends(verify_token)
):
    """Get EPIC FHIR capability statement"""
    try:
        results = await epic_connector.make_fhir_request("metadata", sandbox_mode=sandbox_mode)
        
        return EPICResponse(
            success=True,
            data=results
        )
        
    except Exception as e:
        return EPICResponse(
            success=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

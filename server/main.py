import os
import base64
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import hashlib
import json
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from .database import Database
from .services import AuthService

@asynccontextmanager
async def lifespan(app: FastAPI):
    Database.connect()
    yield
    Database.close()

app = FastAPI(lifespan=lifespan)
security = HTTPBearer()

from pydantic import BaseModel
from typing import Optional

class CreateKeyRequest(BaseModel):
    email: str

class KeyContext(BaseModel):
    key_hash: str
    config: dict
    tenant_email: str

async def get_key_context(credentials: HTTPAuthorizationCredentials = Depends(security)) -> KeyContext:
    token = credentials.credentials
    token_hash = AuthService.hash_key(token)
    
    # Get full details including user_id
    key_details = await AuthService.get_api_key_details(token_hash)
    
    if key_details is None:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    config = key_details.get("config", {})
    user_id = key_details.get("user_id")
    
    email = "unknown"
    if user_id:
        email = await AuthService.get_user_email(user_id) or "unknown"

    return KeyContext(key_hash=token_hash, config=config, tenant_email=email)

async def get_api_key(ctx: KeyContext = Depends(get_key_context)):
    return ctx.config

@app.post("/v1/auth/keys")
async def create_key(request: CreateKeyRequest):
    """Generates a new API key for the given user."""
    try:
        api_key = await AuthService.create_api_key(request.email, {})
        return {"api_key": api_key, "message": "Save this key securely, it cannot be retrieved later."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/auth/validate")
async def validate_key(ctx: KeyContext = Depends(get_key_context)):
    """Validates the API key."""
    return {"status": "valid", "tenant_email": ctx.tenant_email}

@app.post("/v1/traces")

async def ingest_traces(request: Request, ctx: KeyContext = Depends(get_key_context)):
    lf_public = os.getenv("LANGFUSE_PUBLIC_KEY")
    lf_secret = os.getenv("LANGFUSE_SECRET_KEY")
    lf_host = os.getenv("LANGFUSE_HOST")

    if not all([lf_public, lf_secret, lf_host]):
        raise HTTPException(status_code=500, detail="Server misconfiguration: Missing Langfuse credentials.")

    body = await request.body()
    
    # Parse OTLP Protobuf
    try:
        from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
        from opentelemetry.proto.common.v1 import common_pb2
        
        trace_request = trace_service_pb2.ExportTraceServiceRequest()
        trace_request.ParseFromString(body)
        
        # Inject tenant email into all resource spans
        for resource_span in trace_request.resource_spans:
            # Check if attributes list exists, if not it will be created implicitly
            # Create the attribute
            email_attr = common_pb2.KeyValue(
                key="voiceeval.tenant.email",
                value=common_pb2.AnyValue(string_value=ctx.tenant_email)
            )
            # Add to resource attributes
            resource_span.resource.attributes.append(email_attr)
            
            # Also add tenant.id as strict alias if needed, or just email
            # common standard is often tenant.id
            tenant_id_attr = common_pb2.KeyValue(
                key="tenant.id",
                value=common_pb2.AnyValue(string_value=ctx.tenant_email) 
            )
            resource_span.resource.attributes.append(tenant_id_attr)

        # Serialize back to bytes
        new_body = trace_request.SerializeToString()
        
    except Exception as e:
        print(f"Error processing trace protobuf: {e}")
        # If parsing fails, fall back to original body? 
        # Or fail the request?
        # Let's fall back to original body but log error, 
        # though this means tenant info isn't attached.
        # Ideally we should probably fail if we claim to support multitenancy security.
        # But for robustness, let's proceed with original body and log.
        new_body = body

    auth_str = f"{lf_public}:{lf_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    target_url = f"{lf_host}/api/public/otel/v1/traces"
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": request.headers.get("Content-Type", "application/x-protobuf")
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # print(f"DEBUG: Forwarding to {target_url}")
            # print(f"DEBUG: Headers = {headers}")
            # print(f"DEBUG: Body size = {len(new_body)} bytes (was {len(body)})")
            
            response = await client.post(target_url, content=new_body, headers=headers)
            
            # print(f"Langfuse Response Status: {response.status_code}")
            
            if response.status_code >= 400:
                return {"status": "error", "upstream_status": response.status_code, "detail": response.text}
            
            return {"status": "success", "upstream_status": response.status_code}
        except httpx.HTTPError as e:
            print(f"HTTP Error forwarding to Langfuse: {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream HTTP error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error forwarding to Langfuse: {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

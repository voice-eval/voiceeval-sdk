import os
import base64
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import hashlib
import json
from pathlib import Path
from contextlib import asynccontextmanager

# Load Keys from JSON file
KEYS_FILE = Path(__file__).parent / "api_keys.json"
USER_DB = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global USER_DB
    if KEYS_FILE.exists():
        try:
            with open(KEYS_FILE, "r") as f:
                USER_DB = json.load(f)
            print(f"INFO: Loaded {len(USER_DB)} API keys from {KEYS_FILE}")
        except Exception as e:
            print(f"ERROR: Failed to load API keys: {e}")
    else:
        print(f"WARNING: No API keys file found at {KEYS_FILE}")
    yield

app = FastAPI(lifespan=lifespan)
security = HTTPBearer()

async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verify hash
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if token_hash not in USER_DB:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    # Return the hash so we can lookup config in USER_DB
    return token_hash

@app.get("/v1/auth/validate")
async def validate_auth(api_key_hash: str = Depends(get_api_key)):
    """Verifies the API key is valid."""
    return {"status": "valid"}

@app.post("/v1/traces")
async def ingest_traces(request: Request, api_key_hash: str = Depends(get_api_key)):
    config = USER_DB[api_key_hash]
    lf_public = config["langfuse_public"]
    lf_secret = config["langfuse_secret"]
    lf_host = config["langfuse_host"]

    body = await request.body()
    
    auth_str = f"{lf_public}:{lf_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    target_url = f"{lf_host}/api/public/otel/v1/traces"
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": request.headers.get("Content-Type", "application/x-protobuf")
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"DEBUG: Forwarding to {target_url}")
            print(f"DEBUG: Headers = {headers}")
            print(f"DEBUG: Body size = {len(body)} bytes")
            
            response = await client.post(target_url, content=body, headers=headers)
            
            print(f"Langfuse Response Status: {response.status_code}")
            print(f"Langfuse Response Headers: {response.headers}")
            print(f"Langfuse Response Body: {response.text[:500] if response.text else '(empty)'}")
            
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

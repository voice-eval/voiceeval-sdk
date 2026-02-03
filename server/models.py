from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class APIKey(BaseModel):
    key_hash: str = Field(..., alias="_id")
    user_id: str
    config: Dict[str, Any]  # Stores langfuse config etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True

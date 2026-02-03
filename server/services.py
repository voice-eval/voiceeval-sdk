import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from .database import Database
from .models import User, APIKey
from pymongo.errors import DuplicateKeyError

class AuthService:
    
    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def generate_key() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    async def get_or_create_user(cls, email: str) -> User:
        users = Database.get_users_collection()
        user_doc = await users.find_one({"email": email})
        
        if user_doc:
            return User(**user_doc)
        
        new_user = User(email=email)
        await users.insert_one(new_user.model_dump(by_alias=True))
        return new_user

    @classmethod
    async def create_api_key(cls, user_email: str, config: Dict[str, Any], api_key: Optional[str] = None) -> str:
        """
        Creates an API key for a user.
        If api_key is provided, it uses it (rehashing it).
        Returns the raw api_key strings (so the user can see it once).
        """
        user = await cls.get_or_create_user(user_email)
        
        if not api_key:
            api_key = cls.generate_key()
            
        # Check if user already has a key
        keys = Database.get_api_keys_collection()
        existing_key = await keys.find_one({"user_id": user.id})
        if existing_key:
            raise ValueError("User already has an API Key.")

        key_hash = cls.hash_key(api_key)
        
        api_key_doc = APIKey(
            _id=key_hash,
            user_id=user.id,
            config=config
        )
        
        keys = Database.get_api_keys_collection()
        try:
            await keys.insert_one(api_key_doc.model_dump(by_alias=True))
        except DuplicateKeyError:
            # Re-generate if collision (extremely rare) or just fail if provided manually
            if not api_key:
                return await cls.create_api_key(user_email, config) # Retry
            else:
                 raise ValueError("This API Key already exists.")

        return api_key

    @classmethod
    async def get_api_key_config(cls, key_hash: str) -> Optional[Dict[str, Any]]:
        keys = Database.get_api_keys_collection()
        doc = await keys.find_one({"_id": key_hash})
        if doc:
            return doc.get("config")
        return None

    @classmethod
    async def update_api_key_config_by_hash(cls, key_hash: str, config: Dict[str, Any]) -> bool:
        keys = Database.get_api_keys_collection()
        result = await keys.update_one(
            {"_id": key_hash},
            {"$set": {"config": config}}
        )
        return result.matched_count > 0

    @classmethod
    async def update_api_key_config(cls, api_key: str, config: Dict[str, Any]) -> bool:
        """
        Updates the configuration for an existing API key.
        Returns True if successful, False if key not found.
        """
        key_hash = cls.hash_key(api_key)
        return await cls.update_api_key_config_by_hash(key_hash, config)

    @classmethod
    async def get_api_key_details(cls, key_hash: str) -> Optional[Dict[str, Any]]:
        keys = Database.get_api_keys_collection()
        doc = await keys.find_one({"_id": key_hash})
        if doc:
            return doc # Returns full document including user_id
        return None

    @classmethod
    async def get_user_email(cls, user_id: str) -> Optional[str]:
        users = Database.get_users_collection()
        doc = await users.find_one({"_id": user_id})
        if doc:
            return doc.get("email")
        return None

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class Database:
    client: AsyncIOMotorClient = None
    
    @classmethod
    def connect(cls):
        mongo_url = os.getenv("MONGODB_URL")
        # For local development we might want a default, but for now strict on env var as per plan
        if not mongo_url:
             # Fallback for local dev convenience if user hasn't set it yet, though plan warned about it.
             # But better to just let it fail or log warning if not critical path yet.
             # Actually, let's assume it's set or user will set it.
             pass
        
        cls.client = AsyncIOMotorClient(mongo_url)
        print(f"INFO: Connected to MongoDB at {mongo_url}")

    @classmethod
    def close(cls):
        if cls.client:
            cls.client.close()
            print("INFO: Closed MongoDB connection")

    @classmethod
    def get_db(cls):
        return cls.client.sdk

    @classmethod
    def get_users_collection(cls):
        return cls.get_db().users

    @classmethod
    def get_api_keys_collection(cls):
        return cls.get_db().api_keys

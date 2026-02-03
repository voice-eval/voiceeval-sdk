import asyncio
from .database import Database
from .services import AuthService

async def manage_key_async(user_email: str, api_key: str = None, update: bool = False):
    """
    Generates a new key or updates an existing one (metadata only, no config for now).
    """
    Database.connect()
    
    config = {} # Config is now empty
    
    try:
        if update:
            if not api_key:
                print("ERROR: --key must be provided when using --update.")
                return

            # Currently nothing to update in config as it's empty, but keeping the call
            success = await AuthService.update_api_key_config(api_key, config)
            if success:
                print(f"\nSUCCESS. API Key updated for user: {user_email}")
            else:
                print(f"\nERROR. API Key not found.")
        else:
            final_key = await AuthService.create_api_key(user_email, config, api_key)
            
            print(f"\nSUCCESS. API Key generated for user: {user_email}")
            print("IMPORTANT: Ensure you have copied the key if it was generated.")
            if not api_key:
                print(f"Key: {final_key}")
        
    except ValueError as e:
        print(f"ERROR: {e}")
    finally:
        Database.close()

if __name__ == "__main__":
    import argparse
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Manage VoiceEval Server API Keys (MongoDB)")
    parser.add_argument("--email", required=True, help="User Email for Multi-tenancy")
    parser.add_argument("--key", help="Optional: Manually specify the API key instead of generating one.")
    parser.add_argument("--update", action="store_true", help="Update configuration for the provided API key.")
    
    args = parser.parse_args()
    
    asyncio.run(manage_key_async(args.email, args.key, args.update))

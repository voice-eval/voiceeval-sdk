import secrets
import hashlib
import json
from pathlib import Path

KEYS_FILE = Path(__file__).parent / "api_keys.json"

def generate_key():
    """Generates a secure random API key."""
    return secrets.token_urlsafe(32)

def hash_key(key: str) -> str:
    """Hashes the API key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()

def add_key(langfuse_public: str, langfuse_secret: str, langfuse_host: str, api_key: str = None):
    """Generates a new key (or uses provided), hashes it, and saves configuration."""
    if not api_key:
        api_key = generate_key()
        print(f"Generated secure key: {api_key}")
    else:
        print(f"Using provided key: {api_key}")

    key_hash = hash_key(api_key)
    
    if KEYS_FILE.exists():
        with open(KEYS_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        print(f"Creating new keys file at {KEYS_FILE}")
        data = {}
        
    data[key_hash] = {
        "langfuse_public": langfuse_public,
        "langfuse_secret": langfuse_secret,
        "langfuse_host": langfuse_host
    }
    
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"\nSUCCESS. Key hashed and stored in {KEYS_FILE}")
    print("IMPORTANT: Ensure you have copied the key if it was generated.")

if __name__ == "__main__":
    import argparse
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Manage VoiceEval Server API Keys")
    parser.add_argument("--public", default=os.getenv("LANGFUSE_PUBLIC_KEY"), help="Langfuse Public Key (defaults to env LANGFUSE_PUBLIC_KEY)")
    parser.add_argument("--secret", default=os.getenv("LANGFUSE_SECRET_KEY"), help="Langfuse Secret Key (defaults to env LANGFUSE_SECRET_KEY)")
    parser.add_argument("--host", default=os.getenv("LANGFUSE_HOST"), help="Langfuse Host (defaults to env LANGFUSE_HOST)")
    parser.add_argument("--key", help="Optional: Manually specify the API key instead of generating one.")
    
    args = parser.parse_args()
    
    if not all([args.public, args.secret, args.host]):
        print("ERROR: Missing Langfuse credentials. Provide them via arguments or .env file.")
        exit(1)
        
    add_key(args.public, args.secret, args.host, args.key)

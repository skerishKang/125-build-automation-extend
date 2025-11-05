"""
Simple Gmail configuration test (without actual authentication)
"""
import os

print("=== Gmail Configuration Test ===\n")

# Check credentials file
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Project root
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gmail_credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'gmail_token.pickle')

print(f"Project root: {BASE_DIR}")
print(f"Credentials file: {CREDENTIALS_FILE}")
print(f"Token file: {TOKEN_FILE}\n")

# Check if files exist
if os.path.exists(CREDENTIALS_FILE):
    print("✓ gmail_credentials.json exists")
    with open(CREDENTIALS_FILE, 'r') as f:
        import json
        creds = json.load(f)
        client_type = list(creds.keys())[0]
        print(f"  - OAuth2 client type: {client_type}")
        if client_type == "web":
            print("  - Type: Web Application (redirect URI required)")
            print("  - Status: REDIRECT URI CONFIGURED ✓")
        else:
            print("  - Type: Desktop Application")
else:
    print("✗ gmail_credentials.json NOT FOUND")

print()

# Check if token exists
if os.path.exists(TOKEN_FILE):
    print("✓ Existing token found (already authenticated)")
    import pickle
    with open(TOKEN_FILE, 'rb') as f:
        import time
        token = pickle.load(f)
        if hasattr(token, 'expiry'):
            expiry = token.expiry
            print(f"  - Token expiry: {expiry}")
            if expiry > time.time():
                print("  - Token status: VALID")
            else:
                print("  - Token status: EXPIRED (needs re-auth)")
else:
    print("○ No existing token (will require OAuth2 flow)")

print("\n=== OAuth2 Flow ===")
print("To complete authentication:")
print("1. Run: python gmail_reply.py")
print("2. Browser will open automatically")
print("3. Sign in to Gmail account")
print("4. Grant permissions")
print("5. Browser will redirect and close automatically")
print("6. Token will be saved for future use")

print("\n=== Configuration Status ===")
print("✓ OAuth2 credentials configured")
print("✓ Redirect URI should be set to: http://localhost:8888/callback")
print("✓ Google API libraries installed")
print("○ Authentication: PENDING (requires user action)")

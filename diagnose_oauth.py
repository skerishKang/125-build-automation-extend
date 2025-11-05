import sys
import os
sys.path.append('backend')

from services.gmail_reply import CREDENTIALS_FILE, TOKEN_FILE, SCOPES

print("=" * 60)
print("Gmail OAuth2 Problem Diagnosis")
print("=" * 60)

# 1. Check credentials file
print("\n1. Credentials File Check:")
print(f"   Path: {CREDENTIALS_FILE}")
print(f"   Exists: {os.path.exists(CREDENTIALS_FILE)}")
if os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, 'r') as f:
        content = f.read()
        print(f"   Size: {len(content)} bytes")
        print(f"   Preview: {content[:200]}...")
else:
    print("   ERROR: File not found!")

# 2. Check token file
print("\n2. Token File Check:")
print(f"   Path: {TOKEN_FILE}")
print(f"   Exists: {os.path.exists(TOKEN_FILE)}")
if os.path.exists(TOKEN_FILE):
    print(f"   Size: {os.path.getsize(TOKEN_FILE)} bytes")
else:
    print("   INFO: Will be created after first auth")

# 3. Check SCOPES
print("\n3. API SCOPES:")
for scope in SCOPES:
    print(f"   - {scope}")

# 4. Simple auth test
print("\n4. Simple Auth Test:")
try:
    from services.gmail_reply import GmailReplyGenerator
    g = GmailReplyGenerator()
    
    print("   GmailReplyGenerator created OK")
    
    # Try to load client secrets
    import json
    with open(CREDENTIALS_FILE, 'r') as f:
        client_config = json.load(f)
    
    print("   JSON parsing OK")
    print(f"   Installed app config found: {len(client_config.get('installed', {}))} items")
    
    # Check Client ID
    installed = client_config.get('installed', {})
    client_id = installed.get('client_id', 'N/A')
    print(f"   Client ID: {client_id[:30]}...")
    
    # Check Project ID
    project_id = installed.get('project_id', 'N/A')
    print(f"   Project ID: {project_id}")
    
    # Check Auth URI
    auth_uri = installed.get('auth_uri', 'N/A')
    print(f"   Auth URI: {auth_uri}")
    
    # Check Redirect URI
    redirect_uris = installed.get('redirect_uris', [])
    print(f"   Redirect URIs: {redirect_uris}")
    
    print("\n[OK] Credentials file is valid!")
    
    # Check if urn:ietf:wg:oauth:2.0:oob is in redirect URIs
    if 'urn:ietf:wg:oauth:2.0:oob' in redirect_uris:
        print("[OK] Desktop app URI configured")
    else:
        print("[WARN] Desktop app URI NOT configured")
        print("       You need to add 'urn:ietf:wg:oauth:2.0:oob' to redirect URIs")
    
except Exception as e:
    print(f"\n[ERROR] {str(e)[:200]}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnosis Complete")
print("=" * 60)

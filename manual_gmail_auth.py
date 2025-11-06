#!/usr/bin/env python
"""
Manual Gmail OAuth2 Authentication Script
Run this script to authenticate with Gmail OAuth2.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def main():
    print("=" * 70)
    print(" Gmail OAuth2 Authentication")
    print("=" * 70)
    print("\nThis will open your browser and ask you to:")
    print("1. Log in to your Gmail account")
    print("2. Grant permissions to the application")
    print("\nIMPORTANT: Use your PERSONAL Gmail account (not Google Workspace)")
    print("\nPress ENTER when you are ready to start...")
    input()

    print("\nStarting authentication process...\n")

    try:
        from services.gmail import GmailService

        service = GmailService()
        success = service.authenticate()

        if success:
            print("\n" + "=" * 70)
            print(" SUCCESS! Gmail OAuth2 Authentication Completed")
            print("=" * 70)
            print("\nYour personal Gmail account is now connected.")
            print("You can now use /gmail command in Telegram.")

            # Show token location
            import tempfile
            token_path = os.path.join(tempfile.gettempdir(), 'gmail_token.pickle')
            print(f"\nToken file location: {token_path}")

        else:
            print("\n" + "=" * 70)
            print(" ERROR: Authentication Failed")
            print("=" * 70)
            print("\nPlease check the error messages above and try again.")

    except Exception as e:
        print("\n" + "=" * 70)
        print(f" ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

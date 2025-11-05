#!/bin/bash
# Unix/Linux/Mac Shell Script for Sensitive File Protection
# Run this before any git operations

echo "======================================"
echo "[SECURITY] Sensitive File Protection"
echo "======================================"
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo "Running Python security scan..."
    python3 tools/check_secrets.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Security scan failed!"
        echo "Please fix the issues before committing."
        exit 1
    fi
elif command -v python &> /dev/null; then
    echo "Running Python security scan..."
    python tools/check_secrets.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Security scan failed!"
        echo "Please fix the issues before committing."
        exit 1
    fi
else
    echo "Python not found, using alternative checks..."
    echo ""
    echo "Checking for sensitive files in git..."
    if git ls-files --error-unmatch .env gmail_credentials.json service_account.json 2>/dev/null; then
        echo "[ALERT] Sensitive files are tracked by git!"
        exit 1
    else
        echo "[SUCCESS] No sensitive files in git tracking"
    fi
fi

echo ""
echo "[SUCCESS] Security checks passed"
echo "You can safely proceed with git operations"
echo ""

# Set read-only permissions for sensitive files (Linux/Mac only)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "cygwin" ]]; then
    echo "Setting read-only permissions on sensitive files..."
    chmod 400 .env bots/.env gmail_credentials.json service_account.json 2>/dev/null || true
    echo "[DONE] Permissions set"
fi

# Security Policy

## 🔒 Overview

We take the security of 125 Build Automation Extend seriously. This document outlines our security practices and how to report vulnerabilities.

## 🛡️ Security Features

### 1. Credential Protection
- **AES256 Encryption**: All API keys are encrypted before storage
- **Environment Variables**: Sensitive data managed via environment variables
- **Git Ignore**: Comprehensive `.gitignore` prevents accidental credential commits
- **File Permissions**: Recommended 400 permissions for sensitive files

### 2. Authentication
- **Google OAuth2**: Secure multi-user authentication
- **Service Account**: Backend service authentication
- **JWT Tokens**: Stateless authentication for sessions
- **CORS Protection**: Restricts access to authorized domains only

### 3. Data Protection
- **Encryption at Rest**: Database encryption for stored credentials
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Input Validation**: All API inputs validated and sanitized
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

## 🚫 Protected Files

The following files are protected by `.gitignore` and **MUST NEVER** be committed:

### Environment Files
- `.env`
- `.env.local`
- `.env.production`
- `bots/.env`
- `backend/.env`

### Google Credentials
- `service_account.json`
- `gmail_credentials.json`
- `telegram-google.json`
- `*credentials*.json`

### OAuth Tokens
- `gmail_token.pickle`
- `token.pickle`
- `*token*.pickle`

### Database Files
- `*.sqlite-wal`
- `*.sqlite-shm`
- `*.db-wal`

### Other Sensitive Files
- `*secret*.json`
- Private keys, certificates
- Backup files containing credentials

## 🔍 Security Tools

### 1. Pre-commit Hook
```bash
# Automatically checks for sensitive files before commit
# Prevents accidental credential commits
# Located in: .git/hooks/pre-commit
```

### 2. Secret Scanner
```bash
# Run manual security scan
python tools/check_secrets.py

# Checks for:
# - API keys
# - Credentials
# - Sensitive patterns
```

### 3. File Permission Checker
```bash
# Verify secure file permissions
chmod 400 service_account.json bots/.env
```

## ⚠️ Security Best Practices

### For Developers

1. **Never Commit Credentials**
   - Always use `.gitignore` to protect sensitive files
   - Use placeholder values in examples
   - Commit only `.env.example`, never `.env`

2. **API Key Management**
   - Use different API keys for each bot (load distribution)
   - Rotate keys regularly (monthly recommended)
   - Monitor API usage for unauthorized access
   - Revoke compromised keys immediately

3. **Environment Variables**
   - Use environment variables for all secrets
   - Never hardcode credentials in source code
   - Use different values for dev/staging/production

4. **File Permissions**
   ```bash
   # Set restrictive permissions
   chmod 600 .env
   chmod 400 service_account.json
   chmod 600 backend/.env
   ```

5. **Dependency Management**
   ```bash
   # Regularly update dependencies
   pip install --upgrade -r requirements.txt
   
   # Check for known vulnerabilities
   pip-audit
   ```

### For Users

1. **Bot Token Security**
   - Keep your Telegram Bot tokens private
   - Don't share tokens with others
   - Regenerate tokens if compromised
   - Use different tokens for each bot

2. **API Key Rotation**
   - Rotate Gemini API keys monthly
   - Monitor usage patterns
   - Set up billing alerts

3. **Gmail Integration**
   - Use dedicated Gmail account for automation
   - Enable 2FA on associated accounts
   - Regularly review connected apps

## 🐛 Reporting Vulnerabilities

### How to Report

If you discover a security vulnerability, please follow these steps:

1. **DO NOT** create a public GitHub issue
2. Email: [Your Security Email]
3. Include:
   - Vulnerability description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Response Time**: 24-48 hours
- **Initial Assessment**: 3-5 business days
- **Fix Timeline**: Depends on severity
- **Credit**: Acknowledged in security updates (if desired)

### Severity Levels

- **Critical**: Immediate fix required (< 24 hours)
- **High**: Fix within 1 week
- **Medium**: Fix within 1 month
- **Low**: Fix in next release

## 🔧 Security Configuration

### Production Checklist

- [ ] HTTPS enabled for all endpoints
- [ ] Environment variables configured
- [ ] Database credentials secured
- [ ] API keys rotated
- [ ] File permissions set correctly
- [ ] CORS properly configured
- [ ] Logging configured (no sensitive data in logs)
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Dependencies audited

### Redis Security
```bash
# Redis should be:
# - Bound to localhost only (unless using VPC)
# - Password protected (requirepass)
# - Configured with maxmemory and eviction policy
# - Behind firewall (port 6379 not exposed)
```

### File Upload Security
- File type validation
- File size limits
- Malware scanning
- Secure temporary storage

## 📊 Security Monitoring

### Logging
- Authentication attempts
- API key usage
- File access
- Error patterns
- **No sensitive data in logs**

### Alerts
- Failed login attempts
- API quota exceeded
- Unusual access patterns
- File modification detected

## 🔐 Compliance

### Data Privacy
- User data is not shared with third parties
- Data retention policies in place
- Right to data deletion (GDPR)

### Bot Compliance
- Telegram Bot API ToS compliance
- Google API usage policies
- No spam or abuse

## 📚 Resources

### Security Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Telegram Bot API Security](https://core.telegram.org/bots/api)
- [Google API Security](https://cloud.google.com/security)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

### Tools
- [Git-secrets](https://github.com/awslabs/git-secrets) - Prevent committing secrets
- [Bandit](https://bandit.readthedocs.io/) - Python security linting
- [Safety](https://pyup.io/safety/) - Check Python dependencies

## 📝 Changelog

### v1.0.0
- Initial security policy
- Credential protection implemented
- Security scanning tools added

---

## ⚡ Quick Reference

**Emergency Contacts:**
- Security Email: [your-email@domain.com]
- Maintainers: [GitHub usernames]

**Useful Commands:**
```bash
# Scan for secrets
python tools/check_secrets.py

# Fix file permissions
chmod 600 .env && chmod 400 service_account.json

# Update dependencies
pip install --upgrade -r requirements.txt

# Check Redis security
redis-cli config get requirepass
```

**Protected Patterns:**
- `*.env*`
- `*credentials*.json`
- `*token*.pickle`
- `service_account.json`
- `*.sqlite-wal`

---

**Last Updated**: 2025-11-06
**Version**: 1.0.0

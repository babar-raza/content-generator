# Security Best Practices

## API Key Management
- Store in environment variables
- Never commit to git
- Use secrets management in production

## Input Validation
- Schema validation for all inputs
- Sanitize user content
- Rate limiting on endpoints

## Network Security
- Use HTTPS in production
- Firewall configuration
- Restrict Ollama access to localhost

## Access Control
- API key authentication
- Role-based access (future)
- Audit logging

## Regular Updates
```bash
pip install --upgrade -r requirements.txt
git pull origin main
```

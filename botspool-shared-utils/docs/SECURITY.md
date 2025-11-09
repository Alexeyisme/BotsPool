# Security Policy

## Supported Versions

We provide security updates for the following versions of `botspool-shared-utils`:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

### How to Report
If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. **DO NOT** discuss the vulnerability publicly
3. **DO** email us at: security@botspool.ai

### What to Include
Please include the following information in your report:

- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and severity
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Affected Versions**: Which versions are affected
- **Suggested Fix**: If you have a suggested fix
- **Your Contact Information**: For follow-up questions

### Response Timeline
- **Initial Response**: Within 24 hours
- **Status Update**: Within 72 hours
- **Resolution**: Within 30 days (depending on severity)

### Disclosure Process
1. **Report Received**: We acknowledge receipt within 24 hours
2. **Investigation**: We investigate and validate the report
3. **Fix Development**: We develop and test a fix
4. **Release**: We release a security update
5. **Public Disclosure**: We publicly disclose the vulnerability

## Security Features

### Authentication & Authorization
- **JWT Tokens**: RS256 algorithm for secure token signing
- **Password Security**: Bcrypt hashing with configurable rounds
- **Session Management**: Postgres source of truth with Redis cache for resiliency
- **RBAC**: Role-based access control with fine-grained permissions
- **MFA Support**: Multi-factor authentication with TOTP
- **OAuth2**: Secure OAuth2 integration with major providers

### Data Protection
- **Encryption at Rest**: Database and file encryption
- **Encryption in Transit**: TLS for all communications
- **Input Validation**: Comprehensive input validation with Pydantic
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Output encoding and sanitization
- **CSRF Protection**: Token-based CSRF protection

### Error Handling
- **Secure Error Messages**: No sensitive information in error responses
- **Error Logging**: Comprehensive security event logging
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Input Sanitization**: All inputs are validated and sanitized

### Database Security
- **Connection Security**: Encrypted database connections
- **Query Security**: Parameterized queries prevent SQL injection
- **Access Control**: Database access control and permissions
- **Audit Logging**: Database operation audit trails

## Security Best Practices

### For Developers
1. **Keep Dependencies Updated**: Regularly update all dependencies
2. **Use Environment Variables**: Never hardcode secrets
3. **Validate All Inputs**: Always validate and sanitize user inputs
4. **Use HTTPS**: Always use HTTPS in production
5. **Implement Rate Limiting**: Protect against abuse
6. **Log Security Events**: Log all security-relevant events
7. **Use Secure Defaults**: Implement secure default configurations

### For Users
1. **Keep Package Updated**: Always use the latest version
2. **Secure Configuration**: Use secure configuration settings
3. **Monitor Logs**: Monitor application logs for security events
4. **Use Strong Passwords**: Implement strong password policies
5. **Enable MFA**: Enable multi-factor authentication where possible
6. **Regular Backups**: Maintain regular backups of important data

## Security Configuration

### Environment Variables
Secure your environment variables:

```bash
# Required security variables
JWT_PRIVATE_KEY=your_private_key_here
JWT_PUBLIC_KEY=your_public_key_here
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379

# Optional security variables
BCRYPT_ROUNDS=12
JWT_ACCESS_TOKEN_EXPIRY=3600
JWT_REFRESH_TOKEN_EXPIRY=2592000
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### JWT Configuration
Secure JWT configuration:

```python
from botspool_shared_utils.auth import JWTHandler

# Use strong private key (2048+ bits)
jwt_handler = JWTHandler(
    private_key=private_key,  # Strong private key
    public_key=public_key,    # Corresponding public key
    access_token_expiry=3600,  # 1 hour
    refresh_token_expiry=2592000,  # 30 days
    algorithm="RS256"  # Use RS256, not HS256
)
```

### Database Security
Secure database configuration:

```python
from botspool_shared_utils.database import DatabaseManager

# Use encrypted connections
db_manager = DatabaseManager(
    database_url="postgresql://user:pass@localhost/db?sslmode=require",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600    # Recycle connections
)
```

### Rate Limiting
Implement rate limiting:

```python
from botspool_shared_utils.auth import RateLimiter

# Configure rate limiting
rate_limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000,
    requests_per_day=10000
)
```

## Security Monitoring

### Logging
Monitor security events:

```python
import logging
from botspool_shared_utils.logging import get_security_logger

security_logger = get_security_logger()

# Log security events
security_logger.warning(
    "Failed login attempt",
    extra={
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow()
    }
)
```

### Metrics
Track security metrics:

```python
from botspool_shared_utils.monitoring import SecurityMetrics

metrics = SecurityMetrics()

# Track security events
metrics.increment_failed_logins()
metrics.increment_rate_limit_hits()
metrics.increment_suspicious_activity()
```

### Alerts
Set up security alerts:

```python
from botspool_shared_utils.alerts import SecurityAlerts

alerts = SecurityAlerts()

# Send security alerts
alerts.send_failed_login_alert(user_id, ip_address)
alerts.send_rate_limit_alert(user_id, endpoint)
alerts.send_suspicious_activity_alert(user_id, activity)
```

## Vulnerability Management

### Known Vulnerabilities
We maintain a list of known vulnerabilities and their status:

| CVE | Description | Severity | Status | Fixed in |
|-----|-------------|----------|--------|----------|
| - | - | - | - | - |

### Security Updates
Security updates are released as:
- **Patch Releases**: For critical security fixes
- **Minor Releases**: For important security improvements
- **Major Releases**: For significant security changes

### Update Process
1. **Vulnerability Reported**: Security issue is reported
2. **Investigation**: We investigate and validate the issue
3. **Fix Development**: We develop and test a fix
4. **Testing**: Comprehensive testing of the fix
5. **Release**: Security update is released
6. **Notification**: Users are notified of the update

## Compliance

### Security Standards
We follow these security standards:
- **OWASP Top 10**: Protection against common vulnerabilities
- **NIST Cybersecurity Framework**: Comprehensive security framework
- **ISO 27001**: Information security management
- **SOC 2**: Security, availability, and confidentiality

### Data Protection
We implement data protection measures:
- **GDPR Compliance**: European data protection regulation
- **CCPA Compliance**: California consumer privacy act
- **Data Minimization**: Collect only necessary data
- **Right to Erasure**: User data deletion capability
- **Data Portability**: User data export capability

### Audit Trail
We maintain comprehensive audit trails:
- **User Actions**: All user actions are logged
- **System Events**: All system events are recorded
- **Data Access**: All data access is tracked
- **Configuration Changes**: All configuration changes are logged

## Security Testing

### Automated Testing
We use automated security testing:
- **Dependency Scanning**: Scan for vulnerable dependencies
- **Code Analysis**: Static code analysis for security issues
- **Penetration Testing**: Automated penetration testing
- **Vulnerability Scanning**: Regular vulnerability scans

### Manual Testing
We perform manual security testing:
- **Code Review**: Security-focused code reviews
- **Penetration Testing**: Manual penetration testing
- **Security Audits**: Regular security audits
- **Red Team Exercises**: Simulated attack scenarios

### Testing Tools
We use these security testing tools:
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Semgrep**: Static analysis tool
- **OWASP ZAP**: Web application security scanner

## Incident Response

### Response Plan
Our incident response plan includes:
1. **Detection**: Identify security incidents
2. **Assessment**: Assess the severity and impact
3. **Containment**: Contain the incident
4. **Eradication**: Remove the threat
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Document and learn from the incident

### Response Team
Our security response team includes:
- **Security Lead**: Overall incident coordination
- **Technical Lead**: Technical investigation and response
- **Communication Lead**: Internal and external communication
- **Legal Counsel**: Legal and compliance guidance

### Communication
During security incidents:
- **Internal Communication**: Notify internal teams
- **User Communication**: Notify affected users
- **Public Communication**: Public disclosure if necessary
- **Regulatory Communication**: Notify regulators if required

## Contact Information

### Security Team
- **Email**: security@botspool.ai
- **Response Time**: Within 24 hours
- **PGP Key**: Available upon request

### General Security Questions
- **Email**: security-questions@botspool.ai
- **Response Time**: Within 72 hours

### Emergency Contact
- **Email**: security-emergency@botspool.ai
- **Response Time**: Within 4 hours

## Security Resources

### Documentation
- **Security Guide**: Comprehensive security guide
- **Best Practices**: Security best practices
- **Configuration**: Secure configuration examples
- **Troubleshooting**: Security troubleshooting guide

### Tools
- **Security Scanner**: Automated security scanning
- **Vulnerability Database**: Known vulnerability database
- **Security Checklist**: Security implementation checklist
- **Compliance Tools**: Compliance verification tools

### Training
- **Security Training**: Security awareness training
- **Developer Training**: Secure development training
- **Incident Response Training**: Incident response procedures
- **Compliance Training**: Regulatory compliance training

## Acknowledgments

We thank the security community for:
- **Responsible Disclosure**: Following responsible disclosure practices
- **Security Research**: Contributing to security research
- **Bug Reports**: Reporting security vulnerabilities
- **Best Practices**: Sharing security best practices

## License

This security policy is licensed under the MIT License. See the LICENSE file for details.

---

**Last Updated**: January 2024
**Version**: 1.0
**Next Review**: July 2024

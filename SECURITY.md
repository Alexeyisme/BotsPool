# BotsPool Security Guidelines

## 🔒 Security Overview

This document outlines the security best practices, guidelines, and requirements for the BotsPool platform to ensure secure development and deployment.

## 📋 Table of Contents

1. [Security Principles](#1-security-principles)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Data Protection](#3-data-protection)
4. [Network Security](#4-network-security)
5. [Application Security](#5-application-security)
6. [Infrastructure Security](#6-infrastructure-security)
7. [Compliance & Auditing](#7-compliance--auditing)
8. [Incident Response](#8-incident-response)
9. [Security Testing](#9-security-testing)
10. [Security Checklist](#10-security-checklist)

## 1. Security Principles

### 1.1 Core Security Principles

- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimum necessary access rights
- **Zero Trust**: Never trust, always verify
- **Security by Design**: Security built into every component
- **Continuous Monitoring**: Real-time security monitoring
- **Regular Updates**: Keep all components updated

### 1.2 Security Requirements

#### Confidentiality
- All data encrypted at rest and in transit
- Access controls based on user roles
- Secure key management
- Data anonymization for analytics

#### Integrity
- Data validation and sanitization
- Cryptographic signatures for critical data
- Audit trails for all operations
- Version control for configurations

#### Availability
- High availability architecture
- DDoS protection
- Backup and disaster recovery
- Monitoring and alerting

## 2. Authentication & Authorization

### 2.1 Shared Security Utilities

The `botspool-shared-utils` package provides comprehensive security utilities used across all BotsPool services:

#### Authentication Components
- **JWT Management**: RS256 token generation, validation, and refresh
- **RBAC System**: Role-based access control with permission management
- **MFA Support**: Multi-factor authentication with TOTP
- **OAuth2 Integration**: External provider authentication
- **Session Management**: Secure session handling with Redis

#### Encryption & Key Management
- **AES-256-GCM**: Symmetric encryption for sensitive data
- **RSA-2048**: Asymmetric encryption for key exchange
- **Key Management**: Secure key generation, storage, and rotation
- **Password Hashing**: Bcrypt with configurable rounds

#### Data Protection
- **PII Detection**: Automatic identification of sensitive data
- **Data Anonymization**: GDPR-compliant privacy protection
- **Input Validation**: XSS and SQL injection prevention
- **Data Sanitization**: Comprehensive input cleaning

#### Error Handling & Resilience
- **Error Classification**: Security-focused error categorization
- **Circuit Breaker**: Fault tolerance for security services
- **Retry Strategy**: Secure retry mechanisms with backoff
- **Audit Logging**: Security event tracking and monitoring

### 2.2 Authentication

#### JWT Token Security
```python
# botspool-gateway/src/auth/jwt_handler.py
import jwt
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class JWTHandler:
    def __init__(self):
        self.private_key = self._load_private_key()
        self.public_key = self._load_public_key()
        self.algorithm = "RS256"
        self.access_token_expiry = timedelta(hours=1)
        self.refresh_token_expiry = timedelta(days=30)
    
    def generate_token(self, user_id: str, permissions: list) -> dict:
        """Generate secure JWT token"""
        now = datetime.utcnow()
        
        payload = {
            "sub": user_id,
            "iss": "botspool.ai",
            "aud": "botspool-api",
            "iat": now,
            "exp": now + self.access_token_expiry,
            "permissions": permissions,
            "jti": self._generate_jti()  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": int(self.access_token_expiry.total_seconds())
        }
    
    def validate_token(self, token: str) -> dict:
        """Validate JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.public_key, 
                algorithms=[self.algorithm],
                audience="botspool-api",
                issuer="botspool.ai"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        import uuid
        return str(uuid.uuid4())
```

#### Multi-Factor Authentication
```python
# botspool-gateway/src/auth/mfa.py
import pyotp
import qrcode
from io import BytesIO
import base64

class MFAHandler:
    def __init__(self):
        self.issuer_name = "BotsPool"
    
    def generate_secret(self, user_id: str) -> str:
        """Generate TOTP secret for user"""
        secret = pyotp.random_base32()
        
        # Store secret securely (encrypted)
        self._store_secret(user_id, secret)
        
        return secret
    
    def generate_qr_code(self, user_id: str, secret: str) -> str:
        """Generate QR code for MFA setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_id,
            issuer_name=self.issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for API response
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        secret = self._get_secret(user_id)
        totp = pyotp.TOTP(secret)
        
        return totp.verify(token, valid_window=1)
```

### 2.2 Authorization

#### Role-Based Access Control (RBAC)
```python
# botspool-gateway/src/auth/rbac.py
from enum import Enum
from typing import List, Set
from dataclasses import dataclass

class Role(Enum):
    FREE_USER = "free_user"
    BASIC_USER = "basic_user"
    PREMIUM_USER = "premium_user"
    ENTERPRISE_USER = "enterprise_user"
    ADMIN = "admin"
    DEVELOPER = "developer"

class Permission(Enum):
    # Graph permissions
    READ_GRAPHS = "read_graphs"
    WRITE_GRAPHS = "write_graphs"
    ADMIN_GRAPHS = "admin_graphs"
    
    # User permissions
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"
    
    # System permissions
    SYSTEM_ADMIN = "system_admin"
    VIEW_LOGS = "view_logs"
    MANAGE_INFRASTRUCTURE = "manage_infrastructure"

@dataclass
class UserRole:
    role: Role
    permissions: Set[Permission]
    graph_access: Set[str]
    rate_limits: dict

class RBACManager:
    def __init__(self):
        self.role_permissions = {
            Role.FREE_USER: {
                Permission.READ_GRAPHS,
            },
            Role.BASIC_USER: {
                Permission.READ_GRAPHS,
                Permission.WRITE_GRAPHS,
            },
            Role.PREMIUM_USER: {
                Permission.READ_GRAPHS,
                Permission.WRITE_GRAPHS,
                Permission.VIEW_ANALYTICS,
            },
            Role.ENTERPRISE_USER: {
                Permission.READ_GRAPHS,
                Permission.WRITE_GRAPHS,
                Permission.VIEW_ANALYTICS,
                Permission.MANAGE_USERS,
            },
            Role.ADMIN: set(Permission),  # All permissions
            Role.DEVELOPER: {
                Permission.READ_GRAPHS,
                Permission.WRITE_GRAPHS,
                Permission.ADMIN_GRAPHS,
            }
        }
        
        self.graph_access = {
            Role.FREE_USER: {"todo"},
            Role.BASIC_USER: {"todo", "email"},
            Role.PREMIUM_USER: {"todo", "email", "calendar"},
            Role.ENTERPRISE_USER: {"todo", "email", "calendar", "document", "code", "research"},
            Role.ADMIN: set(),  # All graphs
            Role.DEVELOPER: {"todo", "email", "calendar", "document", "code", "research"}
        }
    
    def check_permission(self, user_role: Role, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        return permission in self.role_permissions.get(user_role, set())
    
    def check_graph_access(self, user_role: Role, graph_type: str) -> bool:
        """Check if user role can access specific graph"""
        allowed_graphs = self.graph_access.get(user_role, set())
        return not allowed_graphs or graph_type in allowed_graphs
    
    def get_user_role(self, user_id: str) -> UserRole:
        """Get user role with permissions and access"""
        # This would typically query the database
        role = self._get_user_role_from_db(user_id)
        
        return UserRole(
            role=role,
            permissions=self.role_permissions.get(role, set()),
            graph_access=self.graph_access.get(role, set()),
            rate_limits=self._get_rate_limits(role)
        )
```

## 3. Data Protection

### 3.1 Encryption

#### Data Encryption at Rest
```python
# botspool-shared-utils/src/encryption/data_encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self, password: str = None):
        if password:
            self.key = self._derive_key(password)
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(decoded_data)
        return decrypted_data.decode()
    
    def encrypt_user_data(self, user_id: str, data: dict) -> dict:
        """Encrypt user-specific sensitive data"""
        encrypted_data = {}
        
        sensitive_fields = ['email', 'phone', 'address', 'payment_info']
        
        for key, value in data.items():
            if key in sensitive_fields:
                encrypted_data[key] = self.encrypt_data(str(value))
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        password_bytes = password.encode()
        salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
```

#### Database Encryption
```sql
-- PostgreSQL encryption example
-- Enable transparent data encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive columns
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email_encrypted BYTEA NOT NULL,
    phone_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert encrypted data
INSERT INTO users (user_id, username, email_encrypted, phone_encrypted)
VALUES (
    gen_random_uuid(),
    'john_doe',
    pgp_sym_encrypt('john@example.com', 'encryption_key'),
    pgp_sym_encrypt('+1234567890', 'encryption_key')
);

-- Query encrypted data
SELECT 
    user_id,
    username,
    pgp_sym_decrypt(email_encrypted, 'encryption_key') as email,
    pgp_sym_decrypt(phone_encrypted, 'encryption_key') as phone
FROM users;
```

### 3.2 Data Anonymization

#### PII Anonymization
```python
# botspool-shared-utils/src/anonymization/pii_anonymizer.py
import hashlib
import re
from typing import Dict, Any

class PIIAnonymizer:
    def __init__(self, salt: str):
        self.salt = salt
    
    def anonymize_email(self, email: str) -> str:
        """Anonymize email address"""
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        
        # Hash local part
        hashed_local = hashlib.sha256(
            (local + self.salt).encode()
        ).hexdigest()[:8]
        
        return f"{hashed_local}@{domain}"
    
    def anonymize_phone(self, phone: str) -> str:
        """Anonymize phone number"""
        if not phone:
            return phone
        
        # Keep country code, hash the rest
        if phone.startswith('+'):
            country_code = phone[:3]
            number = phone[3:]
        else:
            country_code = '+1'
            number = phone
        
        hashed_number = hashlib.sha256(
            (number + self.salt).encode()
        ).hexdigest()[:6]
        
        return f"{country_code}***{hashed_number}"
    
    def anonymize_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize user data for analytics"""
        anonymized = data.copy()
        
        if 'email' in anonymized:
            anonymized['email'] = self.anonymize_email(anonymized['email'])
        
        if 'phone' in anonymized:
            anonymized['phone'] = self.anonymize_phone(anonymized['phone'])
        
        if 'user_id' in anonymized:
            anonymized['user_id'] = hashlib.sha256(
                (anonymized['user_id'] + self.salt).encode()
            ).hexdigest()
        
        return anonymized
```

## 4. Network Security

### 4.1 TLS/SSL Configuration

#### NGINX SSL Configuration
```nginx
# nginx-ssl.conf
server {
    listen 443 ssl http2;
    server_name api.botspool.ai;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/botspool.crt;
    ssl_certificate_key /etc/ssl/private/botspool.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://botspool-gateway;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### 4.2 Firewall Configuration

#### UFW Firewall Rules
```bash
#!/bin/bash
# firewall-setup.sh

# Reset firewall
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (change port if needed)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow specific services
ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL (internal)
ufw allow from 10.0.0.0/8 to any port 6379  # Redis (internal)

# Enable firewall
ufw --force enable

# Show status
ufw status verbose
```

## 5. Application Security

### 5.1 Input Validation

#### Request Validation
```python
# botspool-gateway/src/validation/request_validator.py
from pydantic import BaseModel, validator, Field
from typing import Optional, List
import re

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(..., min_length=1, max_length=255)
    session_id: Optional[str] = Field(None, max_length=255)
    context: Optional[dict] = Field(None)
    
    @validator('message')
    def validate_message(cls, v):
        # Check for potential XSS
        if re.search(r'<script|javascript:|data:', v, re.IGNORECASE):
            raise ValueError('Message contains potentially malicious content')
        
        # Check for SQL injection patterns
        if re.search(r'(union|select|insert|update|delete|drop|create|alter)', v, re.IGNORECASE):
            raise ValueError('Message contains potentially malicious SQL patterns')
        
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        # Validate user ID format
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid user ID format')
        
        return v
    
    @validator('context')
    def validate_context(cls, v):
        if v is None:
            return v
        
        # Limit context size
        if len(str(v)) > 10000:
            raise ValueError('Context too large')
        
        return v

class RequestValidator:
    def __init__(self):
        self.max_request_size = 1024 * 1024  # 1MB
        self.max_requests_per_minute = 60
    
    def validate_request(self, request_data: dict) -> ChatRequest:
        """Validate incoming request"""
        try:
            return ChatRequest(**request_data)
        except Exception as e:
            raise ValidationError(f"Request validation failed: {str(e)}")
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize user input"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_str)
        
        # Limit length
        if len(sanitized) > 4000:
            sanitized = sanitized[:4000]
        
        return sanitized.strip()
```

### 5.2 SQL Injection Prevention

#### Parameterized Queries
```python
# botspool-shared-utils/src/database/secure_queries.py
import asyncpg
from typing import List, Dict, Any, Optional

class SecureDatabase:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=20,
            command_timeout=30
        )
    
    async def execute_secure_query(
        self, 
        query: str, 
        *args, 
        fetch: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute parameterized query safely"""
        async with self.pool.acquire() as connection:
            if fetch:
                rows = await connection.fetch(query, *args)
                return [dict(row) for row in rows]
            else:
                await connection.execute(query, *args)
                return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID using parameterized query"""
        query = """
            SELECT user_id, username, email, subscription_tier, created_at
            FROM users 
            WHERE user_id = $1
        """
        
        result = await self.execute_secure_query(query, user_id, fetch=True)
        return result[0] if result else None
    
    async def create_user(
        self, 
        user_id: str, 
        username: str, 
        email: str, 
        password_hash: str
    ) -> None:
        """Create user using parameterized query"""
        query = """
            INSERT INTO users (user_id, username, email, password_hash)
            VALUES ($1, $2, $3, $4)
        """
        
        await self.execute_secure_query(query, user_id, username, email, password_hash)
```

### 5.3 XSS Prevention

#### Output Encoding
```python
# botspool-gateway/src/security/xss_protection.py
import html
import json
from typing import Any

class XSSProtection:
    @staticmethod
    def encode_html(text: str) -> str:
        """Encode text for HTML output"""
        return html.escape(text, quote=True)
    
    @staticmethod
    def encode_json(data: Any) -> str:
        """Encode data for JSON output"""
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    @staticmethod
    def sanitize_response(response_data: dict) -> dict:
        """Sanitize response data"""
        sanitized = {}
        
        for key, value in response_data.items():
            if isinstance(value, str):
                # Encode string values
                sanitized[key] = XSSProtection.encode_html(value)
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = XSSProtection.sanitize_response(value)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [
                    XSSProtection.sanitize_response(item) if isinstance(item, dict)
                    else XSSProtection.encode_html(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
```

## 6. Infrastructure Security

### 6.1 Container Security

#### Secure Dockerfile
```dockerfile
# Dockerfile.secure
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r botspool && useradd -r -g botspool botspool

# Set working directory
WORKDIR /app

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=botspool:botspool . .

# Remove unnecessary files
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -delete

# Switch to non-root user
USER botspool

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Security Scanning
```bash
#!/bin/bash
# security-scan.sh

# Scan Docker image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image botspool/gateway:latest

# Scan for secrets
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image --scanners secret botspool/gateway:latest

# Generate security report
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image --format json --output security-report.json \
    botspool/gateway:latest
```

### 6.2 Kubernetes Security

#### Pod Security Policy
```yaml
# k8s/pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: botspool-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

#### Network Policy
```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: botspool-network-policy
  namespace: botspool
spec:
  podSelector:
    matchLabels:
      app: botspool-gateway
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: botspool
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: botspool
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
```

## 7. Compliance & Auditing

### 7.1 Audit Logging

#### Comprehensive Audit Log
```python
# botspool-gateway/src/audit/audit_logger.py
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class AuditEvent:
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: str
    action: str
    result: str
    details: Dict[str, Any]
    risk_level: str

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for audit logs
        handler = logging.FileHandler('/var/log/botspool/audit.log')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_event(self, event: AuditEvent):
        """Log audit event"""
        # Convert to dict and serialize
        event_dict = asdict(event)
        event_dict['timestamp'] = event.timestamp.isoformat()
        
        # Log as JSON for easy parsing
        self.logger.info(json.dumps(event_dict))
        
        # Also log to security monitoring system
        self._send_to_security_monitoring(event)
    
    def log_authentication(self, user_id: str, success: bool, ip_address: str, details: Dict[str, Any]):
        """Log authentication events"""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type="authentication",
            user_id=user_id,
            session_id=None,
            ip_address=ip_address,
            user_agent=details.get('user_agent'),
            resource="auth",
            action="login",
            result="success" if success else "failure",
            details=details,
            risk_level="high" if not success else "low"
        )
        
        self.log_event(event)
    
    def log_api_access(self, user_id: str, endpoint: str, method: str, success: bool, details: Dict[str, Any]):
        """Log API access events"""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type="api_access",
            user_id=user_id,
            session_id=details.get('session_id'),
            ip_address=details.get('ip_address'),
            user_agent=details.get('user_agent'),
            resource=endpoint,
            action=method,
            result="success" if success else "failure",
            details=details,
            risk_level="medium"
        )
        
        self.log_event(event)
    
    def _send_to_security_monitoring(self, event: AuditEvent):
        """Send event to security monitoring system"""
        # This would integrate with SIEM or security monitoring tools
        pass
```

### 7.2 GDPR Compliance

#### Data Subject Rights
```python
# botspool-gateway/src/compliance/gdpr.py
from typing import Dict, Any, List
from datetime import datetime

class GDPRCompliance:
    def __init__(self, database, audit_logger):
        self.db = database
        self.audit_logger = audit_logger
    
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get all user data (Right to Access)"""
        # Collect all user data from different tables
        user_data = {
            'profile': await self.db.get_user_profile(user_id),
            'subscriptions': await self.db.get_user_subscriptions(user_id),
            'usage_history': await self.db.get_user_usage_history(user_id),
            'chat_history': await self.db.get_user_chat_history(user_id),
            'preferences': await self.db.get_user_preferences(user_id)
        }
        
        # Log data access
        self.audit_logger.log_data_access(user_id, "data_export")
        
        return user_data
    
    async def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (Right to Erasure)"""
        try:
            # Delete from all tables
            await self.db.delete_user_profile(user_id)
            await self.db.delete_user_subscriptions(user_id)
            await self.db.delete_user_usage_history(user_id)
            await self.db.delete_user_chat_history(user_id)
            await self.db.delete_user_preferences(user_id)
            
            # Log data deletion
            self.audit_logger.log_data_deletion(user_id, "gdpr_erasure")
            
            return True
        except Exception as e:
            self.audit_logger.log_error(user_id, "data_deletion_failed", str(e))
            return False
    
    async def update_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user data (Right to Rectification)"""
        try:
            # Update user data
            await self.db.update_user_profile(user_id, data)
            
            # Log data update
            self.audit_logger.log_data_update(user_id, "data_rectification")
            
            return True
        except Exception as e:
            self.audit_logger.log_error(user_id, "data_update_failed", str(e))
            return False
    
    async def export_user_data(self, user_id: str) -> str:
        """Export user data in portable format"""
        user_data = await self.get_user_data(user_id)
        
        # Convert to JSON format
        export_data = {
            'user_id': user_id,
            'export_date': datetime.utcnow().isoformat(),
            'data': user_data
        }
        
        return json.dumps(export_data, indent=2)
```

## 8. Incident Response

### 8.1 Security Incident Response Plan

#### Incident Classification
```python
# botspool-gateway/src/security/incident_response.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentType(Enum):
    DATA_BREACH = "data_breach"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALWARE = "malware"
    DDOS = "ddos"
    INSIDER_THREAT = "insider_threat"
    SYSTEM_COMPROMISE = "system_compromise"

@dataclass
class SecurityIncident:
    incident_id: str
    type: IncidentType
    severity: IncidentSeverity
    description: str
    affected_systems: List[str]
    affected_users: List[str]
    detected_at: datetime
    reported_by: str
    status: str
    response_team: List[str]

class IncidentResponseManager:
    def __init__(self):
        self.incidents = {}
        self.response_procedures = {
            IncidentType.DATA_BREACH: self._handle_data_breach,
            IncidentType.UNAUTHORIZED_ACCESS: self._handle_unauthorized_access,
            IncidentType.DDOS: self._handle_ddos,
            IncidentType.SYSTEM_COMPROMISE: self._handle_system_compromise
        }
    
    def create_incident(self, incident: SecurityIncident) -> str:
        """Create new security incident"""
        self.incidents[incident.incident_id] = incident
        
        # Notify response team
        self._notify_response_team(incident)
        
        # Execute response procedure
        if incident.type in self.response_procedures:
            self.response_procedures[incident.type](incident)
        
        return incident.incident_id
    
    def _handle_data_breach(self, incident: SecurityIncident):
        """Handle data breach incident"""
        # Immediate actions
        self._isolate_affected_systems(incident.affected_systems)
        self._preserve_evidence(incident)
        self._notify_legal_team(incident)
        
        # If high severity, notify authorities
        if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            self._notify_authorities(incident)
    
    def _handle_unauthorized_access(self, incident: SecurityIncident):
        """Handle unauthorized access incident"""
        # Revoke access
        self._revoke_user_access(incident.affected_users)
        
        # Reset credentials
        self._reset_credentials(incident.affected_users)
        
        # Investigate access logs
        self._investigate_access_logs(incident)
    
    def _handle_ddos(self, incident: SecurityIncident):
        """Handle DDoS incident"""
        # Activate DDoS protection
        self._activate_ddos_protection()
        
        # Scale up resources
        self._scale_up_resources()
        
        # Monitor traffic patterns
        self._monitor_traffic_patterns()
    
    def _handle_system_compromise(self, incident: SecurityIncident):
        """Handle system compromise incident"""
        # Isolate compromised systems
        self._isolate_affected_systems(incident.affected_systems)
        
        # Preserve evidence
        self._preserve_evidence(incident)
        
        # Begin forensic investigation
        self._start_forensic_investigation(incident)
```

### 8.2 Security Monitoring

#### Real-time Security Monitoring
```python
# botspool-gateway/src/monitoring/security_monitor.py
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

class SecurityMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'failed_logins': 5,  # per minute
            'api_errors': 100,   # per minute
            'suspicious_requests': 10,  # per minute
            'data_access': 1000  # per minute
        }
        
        self.monitoring_rules = [
            self._detect_brute_force_attacks,
            self._detect_sql_injection_attempts,
            self._detect_xss_attempts,
            self._detect_unusual_data_access,
            self._detect_privilege_escalation
        ]
    
    async def monitor_security_events(self):
        """Monitor security events in real-time"""
        while True:
            try:
                # Get recent events
                events = await self._get_recent_events()
                
                # Apply monitoring rules
                for rule in self.monitoring_rules:
                    alerts = await rule(events)
                    for alert in alerts:
                        await self._handle_security_alert(alert)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Security monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _detect_brute_force_attacks(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect brute force login attempts"""
        alerts = []
        
        # Count failed logins by IP
        failed_logins = {}
        for event in events:
            if event.get('type') == 'authentication' and event.get('result') == 'failure':
                ip = event.get('ip_address')
                if ip:
                    failed_logins[ip] = failed_logins.get(ip, 0) + 1
        
        # Check thresholds
        for ip, count in failed_logins.items():
            if count >= self.alert_thresholds['failed_logins']:
                alerts.append({
                    'type': 'brute_force_attack',
                    'severity': 'high',
                    'ip_address': ip,
                    'count': count,
                    'timestamp': datetime.utcnow()
                })
        
        return alerts
    
    async def _detect_sql_injection_attempts(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect SQL injection attempts"""
        alerts = []
        
        sql_patterns = ['union', 'select', 'insert', 'update', 'delete', 'drop', 'create']
        
        for event in events:
            if event.get('type') == 'api_request':
                message = event.get('message', '').lower()
                for pattern in sql_patterns:
                    if pattern in message:
                        alerts.append({
                            'type': 'sql_injection_attempt',
                            'severity': 'high',
                            'user_id': event.get('user_id'),
                            'ip_address': event.get('ip_address'),
                            'pattern': pattern,
                            'timestamp': datetime.utcnow()
                        })
                        break
        
        return alerts
    
    async def _handle_security_alert(self, alert: Dict[str, Any]):
        """Handle security alert"""
        # Log alert
        print(f"SECURITY ALERT: {alert}")
        
        # Send to security team
        await self._notify_security_team(alert)
        
        # Take automated response if needed
        if alert['severity'] == 'critical':
            await self._take_automated_response(alert)
```

## 9. Security Testing

### 9.1 Automated Security Testing

#### Security Test Suite
```python
# tests/security/test_security.py
import pytest
import requests
from fastapi.testclient import TestClient

class TestSecurity:
    def test_sql_injection_protection(self, client: TestClient):
        """Test SQL injection protection"""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--"
        ]
        
        for payload in malicious_payloads:
            response = client.post(
                "/api/v1/chat/todo",
                json={"message": payload, "user_id": "test_user"}
            )
            
            # Should not return 500 error (SQL error)
            assert response.status_code != 500
            
            # Should return validation error
            assert response.status_code in [400, 422]
    
    def test_xss_protection(self, client: TestClient):
        """Test XSS protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for payload in xss_payloads:
            response = client.post(
                "/api/v1/chat/todo",
                json={"message": payload, "user_id": "test_user"}
            )
            
            # Check response doesn't contain unescaped script tags
            response_text = response.text
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
    
    def test_authentication_required(self, client: TestClient):
        """Test that authentication is required"""
        response = client.post(
            "/api/v1/chat/todo",
            json={"message": "test", "user_id": "test_user"}
        )
        
        assert response.status_code == 401
    
    def test_rate_limiting(self, client: TestClient):
        """Test rate limiting"""
        # Make many requests quickly
        for i in range(100):
            response = client.post(
                "/api/v1/chat/todo",
                json={"message": f"test {i}", "user_id": "test_user"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code == 429
    
    def test_input_validation(self, client: TestClient):
        """Test input validation"""
        invalid_inputs = [
            {"message": "", "user_id": "test_user"},  # Empty message
            {"message": "test", "user_id": ""},       # Empty user_id
            {"message": "x" * 5000, "user_id": "test_user"},  # Too long
            {"message": "test", "user_id": "test_user", "context": "x" * 20000}  # Too large context
        ]
        
        for invalid_input in invalid_inputs:
            response = client.post(
                "/api/v1/chat/todo",
                json=invalid_input,
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
```

### 9.2 Penetration Testing

#### Security Testing Checklist
```bash
#!/bin/bash
# security-test.sh

echo "Starting BotsPool Security Testing..."

# 1. Dependency vulnerability scanning
echo "1. Scanning for vulnerable dependencies..."
safety check -r requirements.txt

# 2. Code security analysis
echo "2. Running static code analysis..."
bandit -r src/ -f json -o security-report.json

# 3. Container security scanning
echo "3. Scanning Docker images..."
trivy image botspool/gateway:latest

# 4. Network security testing
echo "4. Testing network security..."
nmap -sS -O localhost

# 5. SSL/TLS testing
echo "5. Testing SSL/TLS configuration..."
testssl.sh api.botspool.ai

# 6. API security testing
echo "6. Testing API security..."
# Run OWASP ZAP or similar tool
zap-baseline.py -t https://api.botspool.ai

echo "Security testing completed. Check reports for details."
```

## 10. Security Checklist

### 10.1 Development Security Checklist

#### Before Code Review
- [ ] Input validation implemented
- [ ] Output encoding applied
- [ ] SQL injection prevention
- [ ] XSS protection enabled
- [ ] CSRF protection implemented
- [ ] Authentication required
- [ ] Authorization checks in place
- [ ] Error handling secure
- [ ] Logging implemented (no sensitive data)
- [ ] Dependencies updated

#### Before Deployment
- [ ] Security tests passing
- [ ] Vulnerability scan clean
- [ ] Secrets not hardcoded
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Monitoring configured
- [ ] Backup procedures tested
- [ ] Incident response plan ready

### 10.2 Infrastructure Security Checklist

#### Server Security
- [ ] OS updated and patched
- [ ] Firewall configured
- [ ] SSH key authentication
- [ ] Unnecessary services disabled
- [ ] File permissions secured
- [ ] Log monitoring enabled
- [ ] Intrusion detection configured

#### Container Security
- [ ] Non-root user in containers
- [ ] Minimal base images
- [ ] No secrets in images
- [ ] Container scanning clean
- [ ] Resource limits set
- [ ] Security contexts configured

#### Database Security
- [ ] Database encrypted at rest
- [ ] Network access restricted
- [ ] Strong authentication
- [ ] Regular backups
- [ ] Audit logging enabled
- [ ] Connection encryption

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [Security Best Practices](./docs/security-best-practices.md)

## 🚨 Security Contacts

- **Security Team**: security@botspool.ai
- **Incident Response**: incident@botspool.ai
- **Emergency**: +1-XXX-XXX-XXXX

---

*Security is everyone's responsibility. Report security issues immediately to the security team.*

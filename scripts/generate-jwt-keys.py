#!/usr/bin/env python3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Get public key
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

print("=== Private Key ===")
print(private_pem)
print("\n=== Public Key ===")
print(public_pem)
print("\n=== Environment Variables (add to .env) ===")
print(f'JWT_PRIVATE_KEY="{private_pem.replace(chr(10), "\\n")}"')
print(f'JWT_PUBLIC_KEY="{public_pem.replace(chr(10), "\\n")}"')

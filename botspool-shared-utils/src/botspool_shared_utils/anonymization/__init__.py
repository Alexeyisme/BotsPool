"""
PII anonymization and privacy protection utilities for botspool-shared-utils
"""

from .detection import (
    detect_pii,
    detect_email,
    detect_phone,
    detect_credit_card,
    detect_ssn,
    detect_address,
    PIIPattern,
    PIIPatternConfig,
)

from .anonymization import (
    anonymize_data,
    anonymize_email,
    anonymize_phone,
    anonymize_name,
    anonymize_address,
    mask_data,
    hash_data,
    replace_data,
)

# Additional anonymization modules will be added as needed

__all__ = [
    # PII Detection
    "detect_pii",
    "detect_email",
    "detect_phone",
    "detect_credit_card",
    "detect_ssn",
    "detect_address",
    "PIIPattern",
    "PIIPatternConfig",
    # Data Anonymization
    "anonymize_data",
    "anonymize_email",
    "anonymize_phone",
    "anonymize_name",
    "anonymize_address",
    "mask_data",
    "hash_data",
    "replace_data",
]

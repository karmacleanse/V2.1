import random
from datetime import datetime

def generate_registry_id() -> str:
    """Generate unique registry ID in format: KR-YYYY-XX1234"""
    year = datetime.now().year
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    suffix = ''.join(random.choices(chars, k=2))
    num = random.randint(1000, 9999)
    return f'KR-{year}-{suffix}{num}'


def generate_compliance_id() -> str:
    """Generate Compliance Receipt ID in format: KR-TC-YYYY-XX1234"""
    year = datetime.now().year
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    suffix = ''.join(random.choices(chars, k=2))
    num = random.randint(1000, 9999)
    return f'KR-TC-{year}-{suffix}{num}'
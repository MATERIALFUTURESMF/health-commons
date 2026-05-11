import hashlib

# In a real app, this 'SALT' would be a secret key stored safely
SECRET_SALT = "london_material_futures_2026"

def cloak_identity(raw_id: str) -> str:
    """
    Combines a user ID with a secret salt and hashes it.
    This makes 'benjamin' look like 'a8f3...92b1'.
    """
    salted_id = raw_id + SECRET_SALT
    return hashlib.sha256(salted_id.encode()).hexdigest()

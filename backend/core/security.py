import jwt
import os
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-this-in-prod-expediente-abierto")
ALGORITHM = "HS256"

# Aprobado por el usuario: Expiración de 24 hs
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

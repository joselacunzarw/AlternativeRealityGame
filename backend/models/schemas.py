from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

class InboundEmailPayload(BaseModel):
    # Esto simula un payload genérico de proveedores como Resend o SendGrid
    from_email: EmailStr
    to_email: EmailStr
    subject: str
    text: str # Cuerpo limpio del email
    received_at: Optional[datetime] = None

class AgentResponse(BaseModel):
    success: bool
    action: str # Ej: "sent_reply", "escalated_to_director"
    ai_response: Optional[str] = None

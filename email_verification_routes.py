from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
from models import User
import secrets
from email_service import send_verification_email

router = APIRouter(prefix="/api/auth/email", tags=["Email Verification"])

class ResendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Reenviar email de verificação
    """
    try:
        # Buscar usuário
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Não revelar se o email existe ou não (segurança)
            return {"message": "Se o email existir e não estiver verificado, um novo link será enviado."}
        
        # Verificar se já está verificado
        if user.email_verified == 1:
            return {"message": "Este email já está verificado."}
        
        # Gerar novo token
        verification_token = secrets.token_urlsafe(32)
        user.verification_token = verification_token
        db.commit()
        
        # Enviar email
        await send_verification_email(user.email, verification_token)
        
        return {"message": "Se o email existir e não estiver verificado, um novo link será enviado."}
    
    except Exception as e:
        print(f"Erro ao reenviar verificação: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao enviar email de verificação")

@router.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verificar email com token
    """
    try:
        # Buscar usuário pelo token
        user = db.query(User).filter(User.verification_token == token).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Token inválido ou expirado")
        
        # Verificar se já está verificado
        if user.email_verified == 1:
            return {"message": "Email já verificado", "verified": True}
        
        # Marcar como verificado
        user.email_verified = 1
        user.verification_token = None  # Remover token após uso
        db.commit()
        
        return {"message": "Email verificado com sucesso!", "verified": True}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao verificar email: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao verificar email")

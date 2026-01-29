"""
Rotas para recuperação de senha
"""
import os
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from models import User
from security import get_password_hash
from email_service import send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str


def generate_reset_token() -> str:
    """Gera um token seguro para reset de senha"""
    return secrets.token_urlsafe(32)


@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequestIn,
    db: Session = Depends(get_db)
):
    """
    Solicita reset de senha. Envia email com link de reset.
    Sempre retorna sucesso para não vazar informações sobre emails existentes.
    """
    email = payload.email.lower().strip()
    
    # Buscar usuário
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Gerar token de reset
        reset_token = generate_reset_token()
        reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token válido por 1 hora
        
        # Salvar token no banco
        user.reset_token = reset_token
        user.reset_token_expires = reset_token_expires
        db.commit()
        
        # Enviar email
        try:
            send_password_reset_email(user.email, reset_token)
        except Exception as e:
            print(f"Erro ao enviar email de reset: {e}")
            # Não falha a requisição se o email não for enviado
    
    # Sempre retorna sucesso para não vazar se o email existe ou não
    return {
        "message": "Se o email existir em nossa base, você receberá um link para redefinir sua senha."
    }


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirmIn,
    db: Session = Depends(get_db)
):
    """
    Confirma reset de senha com token
    """
    # Validar senha
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter no mínimo 6 caracteres"
        )
    
    # Buscar usuário pelo token
    user = db.query(User).filter(User.reset_token == payload.token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado"
        )
    
    # Verificar se o token expirou
    if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado"
        )
    
    # Atualizar senha
    user.password_hash = get_password_hash(payload.new_password)
    
    # Limpar token de reset
    user.reset_token = None
    user.reset_token_expires = None
    
    db.commit()
    
    return {
        "message": "Senha redefinida com sucesso! Você já pode fazer login com sua nova senha."
    }

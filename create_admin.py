#!/usr/bin/env python3
"""
Script para criar/atualizar usuário admin no Atlas Levels
Uso: python3 create_admin.py
"""
import os
import sys
from getpass import getpass

# Adiciona o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import User
from security import get_password_hash


def create_admin_user(email: str, password: str, role: str = "admin", plan: str = "pro"):
    """
    Cria ou atualiza um usuário admin no banco de dados.
    
    Args:
        email: Email do admin
        password: Senha do admin
        role: Papel do usuário (admin ou user)
        plan: Plano do usuário (brasil, global ou pro)
    """
    # Validações
    email = email.lower().strip()
    password = password.strip()
    role = role.strip().lower()
    plan = plan.strip().lower()
    
    if not email or "@" not in email:
        print("❌ Email inválido!")
        return False
    
    if not password:
        print("❌ Senha não pode ser vazia!")
        return False
    
    if role not in ("user", "admin"):
        print(f"⚠️  Role '{role}' inválido. Usando 'admin'.")
        role = "admin"
    
    if plan not in ("brasil", "global", "pro"):
        print(f"⚠️  Plan '{plan}' inválido. Usando 'pro'.")
        plan = "pro"
    
    # Proteção contra senha muito longa (bcrypt tem limite de 72 bytes)
    pw_bytes = len(password.encode("utf-8"))
    if pw_bytes > 72:
        print(f"⚠️  Senha muito longa ({pw_bytes} bytes). Truncando para 72 bytes.")
        password = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    
    # Cria as tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    
    # Cria sessão do banco
    db: Session = SessionLocal()
    
    try:
        # Verifica se usuário já existe
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Atualiza usuário existente
            user.password_hash = get_password_hash(password)
            user.role = role
            user.plan = plan
            db.commit()
            print(f"✅ Usuário admin '{email}' atualizado com sucesso!")
            print(f"   Role: {role}")
            print(f"   Plan: {plan}")
        else:
            # Cria novo usuário
            new_user = User(
                email=email,
                password_hash=get_password_hash(password),
                role=role,
                plan=plan
            )
            db.add(new_user)
            db.commit()
            print(f"✅ Usuário admin '{email}' criado com sucesso!")
            print(f"   Role: {role}")
            print(f"   Plan: {plan}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar/atualizar admin: {e}")
        return False
    
    finally:
        db.close()


def main():
    """Função principal do script."""
    print("=" * 60)
    print("Atlas Levels - Criação de Usuário Admin")
    print("=" * 60)
    print()
    
    # Coleta informações do usuário
    email = input("Email do admin: ").strip()
    password = getpass("Senha do admin: ").strip()
    password_confirm = getpass("Confirme a senha: ").strip()
    
    if password != password_confirm:
        print("❌ As senhas não coincidem!")
        sys.exit(1)
    
    role = input("Role [admin]: ").strip() or "admin"
    plan = input("Plan [pro]: ").strip() or "pro"
    
    print()
    print("Criando usuário admin...")
    
    success = create_admin_user(email, password, role, plan)
    
    if success:
        print()
        print("=" * 60)
        print("✅ Credenciais de admin configuradas com sucesso!")
        print("=" * 60)
        print()
        print("Você pode fazer login com:")
        print(f"  Email: {email}")
        print(f"  Senha: {'*' * len(password)}")
        print()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

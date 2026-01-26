"""
Rotas Admin - Protegidas Globalmente
Todas as rotas neste router requerem autenticação admin
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserListOut, UserOut, UserCreateIn, UserUpdateIn
from security import require_admin, get_password_hash

# Router com proteção global - TODAS as rotas requerem admin
admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)]  # 🔒 Proteção global
)


# =========================
# USER MANAGEMENT
# =========================

@admin_router.get("/users", response_model=UserListOut)
def list_users(db: Session = Depends(get_db)):
    """Lista todos os usuários (apenas admin)"""
    users = db.query(User).all()
    return UserListOut(users=[
        UserOut(
            id=u.id,
            email=u.email,
            role=u.role,
            plan=u.plan,
            created_at=u.created_at
        ) for u in users
    ])


@admin_router.post("/users", response_model=UserOut)
def create_user(payload: UserCreateIn, db: Session = Depends(get_db)):
    """Cria um novo usuário (apenas admin)"""
    email = payload.email.lower().strip()
    
    # Verificar se já existe
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    new_user = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        plan=payload.plan
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserOut(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        plan=new_user.plan,
        created_at=new_user.created_at
    )


@admin_router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateIn, db: Session = Depends(get_db)):
    """Atualiza um usuário (apenas admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if payload.role:
        user.role = payload.role
    if payload.plan:
        user.plan = payload.plan
    if payload.new_password:
        user.password_hash = get_password_hash(payload.new_password)
    
    db.commit()
    db.refresh(user)
    
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        plan=user.plan,
        created_at=user.created_at
    )


@admin_router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """Deleta um usuário (apenas admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Proteção: não pode deletar a si mesmo
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta")
    
    db.delete(user)
    db.commit()
    
    return {"message": f"Usuário {user.email} deletado com sucesso"}


# =========================
# SECURITY MONITORING
# =========================

@admin_router.get("/security/stats")
def get_security_stats():
    """Retorna estatísticas de segurança (apenas admin)"""
    from security_monitor import security_monitor
    return security_monitor.get_stats()

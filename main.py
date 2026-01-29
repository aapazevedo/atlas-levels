import os
import csv
import io
import logging
from datetime import datetime, date
from typing import Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, DailyLevels, Payment
from schemas import (
    LoginIn, TokenOut,
    LevelsOut, LevelsUpsertIn, SymbolListOut,
    UserListOut, UserOut, UserCreateIn, UserUpdateIn
)
from security import verify_password, get_password_hash, create_access_token, get_current_user, require_admin
from email_service import send_welcome_email, send_payment_confirmation_email
from security_middleware import SecurityHeadersMiddleware
from rate_limiter import limiter, LOGIN_LIMIT, ADMIN_LIMIT
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from exception_handlers import validation_exception_handler, generic_exception_handler
from fastapi.exceptions import RequestValidationError
from security_monitor import security_monitor

APP_NAME = os.getenv("APP_NAME", "Atlas Levels — Institutional Zones")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

# Configurar rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception handlers customizados (previne vazamento de informações)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware de segurança (deve vir primeiro)
app.add_middleware(SecurityHeadersMiddleware)

# CORS - Restrito ao domínio de produção
# Em desenvolvimento local, adicione "http://localhost:3000" se necessário
allowed_origins = [
    "https://atlas-levels-api.onrender.com",
    "http://localhost:8000",  # Para testes locais
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")

# Importar rotas de pagamento
from payment_routes import router as payment_router
app.include_router(payment_router)

# Importar rotas admin (protegidas globalmente)
from admin_routes import admin_router
app.include_router(admin_router)

# Importar rotas de recuperação de senha
from password_reset_routes import router as password_reset_router
app.include_router(password_reset_router)

from email_verification_routes import router as email_verification_router
app.include_router(email_verification_router)


# =========================================================
# BOOTSTRAP ADMIN (UPSERT + PROTEÇÃO 72 BYTES)
# =========================================================
@app.on_event("startup")
def bootstrap_admin():

    email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "admin@atlaslevels.pro").lower().strip()
    password = (os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "admin123").strip()
    role = (os.getenv("BOOTSTRAP_ADMIN_ROLE") or "admin").strip().lower()
    plan = (os.getenv("BOOTSTRAP_ADMIN_PLAN") or "pro").strip().lower()

    if role not in ("user", "admin"):
        role = "admin"
    if plan not in ("brasil", "global", "pro"):
        plan = "pro"

    # DEBUG: mostra quantos bytes chegaram da senha
    pw_bytes = len(password.encode("utf-8"))
    print(f"ℹ️ BOOTSTRAP: senha recebida tem {pw_bytes} bytes")

    # Proteção: nunca deixa o bcrypt quebrar
    if pw_bytes > 72:
        print("⚠️ BOOTSTRAP: senha >72 bytes. Truncando automaticamente.")
        password = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        u = db.query(User).filter(User.email == email).first()

        if not u:
            u = User(
                email=email,
                password_hash=get_password_hash(password),
                role=role,
            )
            if hasattr(u, "plan"):
                u.plan = plan

            db.add(u)
            db.commit()
            print("✅ BOOTSTRAP: admin criado no banco.")

        else:
            u.role = role
            u.password_hash = get_password_hash(password)
            if hasattr(u, "plan"):
                u.plan = plan

            db.commit()
            print("✅ BOOTSTRAP: admin atualizado no banco.")

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"⚠️ BOOTSTRAP: erro ao criar/atualizar admin: {e}")

    finally:
        try:
            db.close()
        except Exception:
            pass


# =========================
# PÁGINAS
# =========================
@app.get("/", response_class=HTMLResponse)
def landing():
    with open(os.path.join(WEB_DIR, "landing.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/app", response_class=HTMLResponse)
def app_page():
    with open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/payment", response_class=HTMLResponse)
def payment_page():
    with open(os.path.join(WEB_DIR, "payment.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    with open(os.path.join(WEB_DIR, "signup.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
    with open(os.path.join(WEB_DIR, "forgot-password.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page():
    with open(os.path.join(WEB_DIR, "reset-password.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/verify-email", response_class=HTMLResponse)
def verify_email_page():
    with open(os.path.join(WEB_DIR, "verify-email.html"), encoding="utf-8") as f:
        return f.read()


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Endpoint de health check para diagnóstico"""
    try:
        from sqlalchemy import text, inspect
        from database import DATABASE_URL
        
        # Testar conexão com banco
        db.execute(text("SELECT 1"))
        
        # Usar inspector do SQLAlchemy (funciona com qualquer banco)
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        # Verificar colunas da tabela users
        columns = []
        if 'users' in tables:
            columns_info = inspector.get_columns('users')
            columns = [col['name'] for col in columns_info]
        
        return {
            "status": "healthy",
            "database": "connected",
            "database_type": DATABASE_URL.split("://")[0],
            "database_url": DATABASE_URL.split("://")[0] + "://***",
            "tables": tables,
            "users_columns": columns,
            "subscription_expires_exists": "subscription_expires" in columns
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# =========================
# AUTH
# =========================
@app.post("/api/v1/auth/login", response_model=TokenOut)
@app.post("/api/auth/login", response_model=TokenOut, deprecated=True)  # Manter compatibilidade
@limiter.limit(LOGIN_LIMIT)
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    try:
        logger.info(f"Login attempt for: {payload.email}")
        
        # Verificar se IP está bloqueado
        client_ip = request.client.host
        if security_monitor.is_blocked(client_ip):
            logger.warning(f"Blocked IP attempt: {client_ip}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso temporariamente bloqueado")
        
        user = db.query(User).filter(User.email == payload.email.lower()).first()
        logger.info(f"User found: {user is not None}")
        
        if not user or not verify_password(payload.password, user.password_hash):
            # Registrar tentativa falhada
            security_monitor.record_failed_login(client_ip, payload.email)
            logger.warning(f"Invalid credentials for: {payload.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

        logger.info(f"Login successful for: {payload.email}")
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return TokenOut(access_token=token, token_type="bearer", email=user.email, role=user.role)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {payload.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno do servidor. Tente novamente mais tarde.")


@app.get("/api/v1/auth/me")
@app.get("/api/auth/me", deprecated=True)  # Manter compatibilidade
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Retorna informações do usuário autenticado"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "plan": current_user.plan
    }


@app.post("/api/auth/register", response_model=TokenOut)
def register(payload: LoginIn, db: Session = Depends(get_db)):
    """Registra um novo usuário"""
    email = payload.email.lower().strip()
    
    # Verificar se o email já existe
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")
    
    # Validar senha (mínimo 6 caracteres)
    if len(payload.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha deve ter no mínimo 6 caracteres")
    
    # Criar novo usuário
    new_user = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        role="user",
        plan="free"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Enviar email de boas-vindas
    try:
        send_welcome_email(new_user.email)
    except Exception as e:
        print(f"Erro ao enviar email de boas-vindas: {e}")
    
    # Gerar token para login automático
    token = create_access_token({"sub": str(new_user.id), "role": new_user.role})
    return TokenOut(access_token=token, token_type="bearer", email=new_user.email, role=new_user.role)


@app.post("/api/auth/token", response_model=TokenOut)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    t = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenOut(access_token=t, token_type="bearer", email=user.email, role=user.role)


# =========================
# PLANOS E ATIVOS
# =========================
@app.get("/api/symbols", response_model=SymbolListOut)
def list_symbols(user=Depends(get_current_user)):
    brasil = ["WIN", "WDO", "BIT"]
    global_ = ["BTCUSD", "XAUUSD", "ES", "NAS100", "US30",
               "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "WTI"]

    plan = getattr(user, "plan", "pro")

    if plan == "brasil":
        symbols = brasil
    elif plan == "global":
        symbols = global_
    else:
        symbols = brasil + global_

    symbols = list(dict.fromkeys(symbols))
    return SymbolListOut(symbols=symbols)


# =========================
# LEVELS
# =========================
@app.get("/api/levels", response_model=LevelsOut)
def get_levels(symbol: str, valid_for: Optional[date] = None,
               user=Depends(get_current_user), db: Session = Depends(get_db)):

    sym = symbol.upper().strip()
    valid_for = valid_for or date.today()

    row = db.query(DailyLevels).filter(
        DailyLevels.symbol == sym,
        DailyLevels.valid_for == valid_for
    ).order_by(DailyLevels.created_at.desc()).first()

    if not row:
        raise HTTPException(status_code=404, detail="Níveis não encontrados.")

    return LevelsOut(
        symbol=row.symbol,
        valid_for=row.valid_for,
        trade_date=row.trade_date,
        levels={
            "vah": row.vah,
            "val": row.val,
            "lvn": [row.lvn1] if row.lvn1 is not None else [],
            "institutional_buy": row.inst_buy,
            "institutional_sell": row.inst_sell
        }
    )

# =========================
# ROTAS ANTIGAS (DEPRECATED) - Manter compatibilidade
# =========================
# As rotas antigas redirecionam para o novo admin_router
# Mantidas apenas para compatibilidade com frontend antigo

@app.get("/api/admin/users", response_model=UserListOut, deprecated=True)
def list_users_old(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """[DEPRECATED] Use /api/v1/admin/users"""
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

@app.post("/api/admin/users", response_model=UserOut, deprecated=True)
def create_user_old(payload: UserCreateIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """[DEPRECATED] Use /api/v1/admin/users"""
    email = payload.email.lower().strip()
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

@app.put("/api/admin/users/{user_id}", response_model=UserOut, deprecated=True)
def update_user_old(user_id: int, payload: UserUpdateIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """[DEPRECATED] Use /api/v1/admin/users/{user_id}"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if payload.new_password:
        user.password_hash = get_password_hash(payload.new_password)
    if payload.role:
        user.role = payload.role
    if payload.plan:
        user.plan = payload.plan
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        plan=user.plan,
        created_at=user.created_at
    )

@app.delete("/api/admin/users/{user_id}", deprecated=True)
def delete_user_old(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """[DEPRECATED] Use /api/v1/admin/users/{user_id}"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Não é possível deletar seu próprio usuário")
    db.delete(user)
    db.commit()
    return {"message": "Usuário deletado com sucesso"}

@app.get("/api/admin/security/stats", deprecated=True)
def get_security_stats_old(admin=Depends(require_admin)):
    """[DEPRECATED] Use /api/v1/admin/security/stats"""
    return security_monitor.get_stats()

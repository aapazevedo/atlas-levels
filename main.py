import os
import csv
import io
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
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
from security import (
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    get_password_hash,
)

APP_NAME = os.getenv("APP_NAME", "Atlas Levels — Institutional Zones")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")

# Importar rotas de pagamento
from payment_routes import router as payment_router
app.include_router(payment_router)


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


# =========================
# AUTH
# =========================
@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenOut(access_token=token, token_type="bearer", email=user.email, role=user.role)


@app.get("/api/auth/me")
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
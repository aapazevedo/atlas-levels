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
from models import User, DailyLevels
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
    oauth2_scheme,
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


# =========================================================
# BOOTSTRAP ADMIN (cria/atualiza admin no Postgres)
# =========================================================
@app.on_event("startup")
def bootstrap_admin():
    """
    Cria um usuário admin automaticamente na inicialização.

    Por padrão:
      - cria SOMENTE se ainda não existir no banco

    Se você setar:
      - BOOTSTRAP_ADMIN_RESET=1
    então:
      - atualiza senha/role/plan mesmo se já existir.

    Variáveis (Render > Environment):
      - BOOTSTRAP_ADMIN_EMAIL
      - BOOTSTRAP_ADMIN_PASSWORD
      - BOOTSTRAP_ADMIN_ROLE (default: admin)
      - BOOTSTRAP_ADMIN_PLAN (default: pro)
      - BOOTSTRAP_ADMIN_RESET (default: 0)
    """
    email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "admin@atlaslevels.pro").lower().strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "admin123"
    role = (os.getenv("BOOTSTRAP_ADMIN_ROLE") or "admin").strip().lower()
    plan = (os.getenv("BOOTSTRAP_ADMIN_PLAN") or "pro").strip().lower()
    reset = (os.getenv("BOOTSTRAP_ADMIN_RESET") or "0").strip() in ("1", "true", "TRUE", "yes", "YES")

    # validações simples
    if role not in ("user", "admin"):
        role = "admin"
    if plan not in ("brasil", "global", "pro"):
        plan = "pro"

    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        exists = db.query(User).filter(User.email == email).first()

        if not exists:
            u = User(
                email=email,
                password_hash=get_password_hash(password),
                role=role,
            )
            if hasattr(u, "plan"):
                u.plan = plan
            db.add(u)
            db.commit()
            print("✅ BOOTSTRAP: admin criado automaticamente no banco.")

        else:
            if reset:
                exists.password_hash = get_password_hash(password)
                exists.role = role
                if hasattr(exists, "plan"):
                    exists.plan = plan
                db.commit()
                print("✅ BOOTSTRAP: admin EXISTIA — senha/role/plan ATUALIZADOS (RESET=1).")
            else:
                print("ℹ️ BOOTSTRAP: admin já existe no banco. (RESET=0, nada alterado)")

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
        try:
            db_gen.close()
        except Exception:
            pass


@app.get("/", response_class=HTMLResponse)
def landing():
    with open(os.path.join(WEB_DIR, "landing.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/app", response_class=HTMLResponse)
def app_page():
    with open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


# =========================
# AUTH (JSON login - painel)
# =========================
@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenOut(access_token=token, token_type="bearer", email=user.email, role=user.role)


# =========================
# AUTH (Swagger Authorize)
# =========================
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


@app.post("/api/admin/levels", response_model=LevelsOut)
def upsert_levels(payload: LevelsUpsertIn, admin=Depends(require_admin), db: Session = Depends(get_db)):
    sym = payload.symbol.upper().strip()

    row = db.query(DailyLevels).filter(
        DailyLevels.symbol == sym,
        DailyLevels.valid_for == payload.valid_for
    ).first()

    if row:
        row.trade_date = payload.trade_date
        row.vah = payload.vah
        row.val = payload.val
        row.lvn1 = payload.lvn1
        row.inst_buy = payload.inst_buy
        row.inst_sell = payload.inst_sell
        row.created_at = datetime.utcnow()
    else:
        db.add(DailyLevels(
            symbol=sym,
            trade_date=payload.trade_date,
            valid_for=payload.valid_for,
            vah=payload.vah,
            val=payload.val,
            lvn1=payload.lvn1,
            inst_buy=payload.inst_buy,
            inst_sell=payload.inst_sell
        ))

    db.commit()
    return get_levels(sym, payload.valid_for, admin, db)


# =========================
# IMPORTAÇÃO CSV (ADMIN)
# =========================
@app.post("/api/admin/import_csv")
def import_csv(file: UploadFile = File(...),
               admin=Depends(require_admin),
               db: Session = Depends(get_db)):

    content = file.file.read().decode("utf-8-sig", errors="ignore")
    sep = ";" if content.count(";") > content.count(",") else ","
    reader = csv.DictReader(io.StringIO(content), delimiter=sep)

    required = {"symbol", "valid_for", "vah", "val", "lvn1", "inst_buy", "inst_sell"}
    cols = set(reader.fieldnames or [])
    if not required.issubset(cols):
        raise HTTPException(status_code=400, detail=f"CSV inválido. Precisa conter: {sorted(required)}")

    def pdate(x):
        x = (x or "").strip()
        return datetime.strptime(x, "%Y-%m-%d").date() if x else None

    def pfloat(x):
        x = (x or "").strip()
        if not x:
            return None
        return float(x.replace(",", "."))

    inserted = updated = 0

    for r in reader:
        sym = (r.get("symbol") or "").strip().upper()
        valid_for = pdate(r.get("valid_for"))
        trade_date = pdate(r.get("trade_date"))

        vah = pfloat(r.get("vah"))
        val = pfloat(r.get("val"))
        lvn1 = pfloat(r.get("lvn1"))
        inst_buy = pfloat(r.get("inst_buy"))
        inst_sell = pfloat(r.get("inst_sell"))

        if not sym or not valid_for:
            continue
        if vah is None or val is None or inst_buy is None or inst_sell is None:
            continue

        row = db.query(DailyLevels).filter(
            DailyLevels.symbol == sym,
            DailyLevels.valid_for == valid_for
        ).first()

        if row:
            row.trade_date = trade_date
            row.vah = vah
            row.val = val
            row.lvn1 = lvn1
            row.inst_buy = inst_buy
            row.inst_sell = inst_sell
            row.created_at = datetime.utcnow()
            updated += 1
        else:
            db.add(DailyLevels(
                symbol=sym,
                valid_for=valid_for,
                trade_date=trade_date,
                vah=vah,
                val=val,
                lvn1=lvn1,
                inst_buy=inst_buy,
                inst_sell=inst_sell
            ))
            inserted += 1

    db.commit()
    return {"ok": True, "inserted": inserted, "updated": updated}


# =========================
# USERS ADMIN (PAINEL)
# =========================
@app.get("/api/admin/users", response_model=UserListOut)
def list_users(admin=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    out = [UserOut(id=u.id, email=u.email, role=u.role, plan=getattr(u, "plan", "pro")) for u in users]
    return UserListOut(users=out)


@app.post("/api/admin/users", response_model=UserOut)
def create_user(payload: UserCreateIn, admin=Depends(require_admin), db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email já existe.")

    role = payload.role if payload.role in ("user", "admin") else "user"
    plan = payload.plan if payload.plan in ("brasil", "global", "pro") else "brasil"

    u = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        role=role,
    )
    if hasattr(u, "plan"):
        u.plan = plan

    db.add(u)
    db.commit()
    db.refresh(u)

    return UserOut(id=u.id, email=u.email, role=u.role, plan=getattr(u, "plan", plan))


@app.patch("/api/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateIn, admin=Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if payload.role is not None:
        if payload.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="role inválido (use user|admin).")
        u.role = payload.role

    if payload.plan is not None:
        if payload.plan not in ("brasil", "global", "pro"):
            raise HTTPException(status_code=400, detail="plan inválido (use brasil|global|pro).")
        if hasattr(u, "plan"):
            u.plan = payload.plan

    if payload.new_password is not None:
        u.password_hash = get_password_hash(payload.new_password)

    db.commit()
    db.refresh(u)
    return UserOut(id=u.id, email=u.email, role=u.role, plan=getattr(u, "plan", "pro"))
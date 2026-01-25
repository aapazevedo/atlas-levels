from datetime import date, timedelta
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import User, DailyLevels
from security import get_password_hash

Base.metadata.create_all(bind=engine)

def upsert_user(db: Session, email: str, password: str, role: str, plan: str):
    email = email.lower().strip()
    u = db.query(User).filter(User.email == email).first()
    if u:
        u.password_hash = get_password_hash(password)
        u.role = role
        u.plan = plan
    else:
        db.add(User(
            email=email,
            password_hash=get_password_hash(password),
            role=role,
            plan=plan
        ))
    db.commit()

def upsert_levels(db: Session, symbol: str, valid_for: date, trade_date: date,
                  vah: float, val: float, lvn1: float, inst_buy: float, inst_sell: float):

    symbol = symbol.upper().strip()
    row = db.query(DailyLevels).filter(
        DailyLevels.symbol == symbol,
        DailyLevels.valid_for == valid_for
    ).first()

    if row:
        row.trade_date = trade_date
        row.vah = vah
        row.val = val
        row.lvn1 = lvn1
        row.inst_buy = inst_buy
        row.inst_sell = inst_sell
    else:
        db.add(DailyLevels(
            symbol=symbol,
            valid_for=valid_for,
            trade_date=trade_date,
            vah=vah,
            val=val,
            lvn1=lvn1,
            inst_buy=inst_buy,
            inst_sell=inst_sell
        ))

    db.commit()

def main():
    db = SessionLocal()
    try:
        # Usuários iniciais
        upsert_user(db, "admin@atlaslevels.pro", "admin123", "admin", "pro")
        upsert_user(db, "demo@atlaslevels.pro", "demo123", "user", "brasil")

        today = date.today()
        trade_date = today - timedelta(days=1)

        samples = {
            "WIN":   (132410, 131920, 132180, 131780, 132540),
            "WDO":   (5042,   4988,   5012,   4996,   5031),
            "BIT":   (245000, 238500, 241300, 239200, 243900),
        }

        for sym, (vah, val, lvn1, ib, isell) in samples.items():
            upsert_levels(db, sym, today, trade_date, vah, val, lvn1, ib, isell)

        print("OK: banco criado.")
        print("Admin (pro): admin@atlaslevels.pro / admin123")
        print("Demo (brasil): demo@atlaslevels.pro / demo123")

    finally:
        db.close()

if __name__ == "__main__":
    main()

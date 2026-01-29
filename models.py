from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Index
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="user", nullable=False)   # admin | user
    plan = Column(String(32), default="pro", nullable=False)    # brasil | global | pro
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    subscription_expires = Column(DateTime, nullable=True)  # Data de vencimento da assinatura
    reset_token = Column(String(255), nullable=True)  # Token para reset de senha
    reset_token_expires = Column(DateTime, nullable=True)  # Expiração do token de reset

class DailyLevels(Base):
    __tablename__ = "daily_levels"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    trade_date = Column(Date, nullable=True)
    valid_for = Column(Date, index=True, nullable=False)

    vah = Column(Float, nullable=False)
    val = Column(Float, nullable=False)
    lvn1 = Column(Float, nullable=True)

    inst_buy = Column(Float, nullable=False)
    inst_sell = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_levels_symbol_validfor", "symbol", "valid_for"),)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    plan = Column(String(32), nullable=False)  # brasil | global | pro
    amount = Column(Float, nullable=False)
    payment_method = Column(String(32), nullable=False)  # pix | credit_card
    mp_payment_id = Column(String(255), index=True, nullable=True)
    status = Column(String(32), default="pending", nullable=False)  # pending | approved | rejected | cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

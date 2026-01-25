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

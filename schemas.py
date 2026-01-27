from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# =====================
# AUTH
# =====================
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str
    email: EmailStr
    role: str

# =====================
# SYMBOLS
# =====================
class SymbolListOut(BaseModel):
    symbols: List[str]

# =====================
# LEVELS
# =====================
class LevelsUpsertIn(BaseModel):
    symbol: str
    valid_for: date
    trade_date: Optional[date] = None
    vah: float
    val: float
    lvn1: Optional[float] = None
    inst_buy: float
    inst_sell: float

class LevelsOut(BaseModel):
    symbol: str
    valid_for: date
    trade_date: Optional[date] = None
    levels: Dict[str, Any]

# =====================
# USERS (ADMIN)
# =====================
class UserOut(BaseModel):
    """Schema de resposta de usuário - nunca inclui password_hash"""
    id: int
    email: EmailStr
    role: str
    plan: str
    created_at: Optional[datetime] = None
    subscription_expires: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserListOut(BaseModel):
    users: List[UserOut]

class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    role: str = Field(default="user")     # user | admin
    plan: str = Field(default="brasil")   # brasil | global | pro

class UserUpdateIn(BaseModel):
    role: Optional[str] = None            # user | admin
    plan: Optional[str] = None            # brasil | global | pro
    new_password: Optional[str] = Field(default=None, min_length=4)
    subscription_expires: Optional[datetime] = None

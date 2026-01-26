"""
Rate Limiting para Atlas Levels
Protege contra ataques de força bruta e DDoS
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


# Configurar limiter
limiter = Limiter(key_func=get_remote_address)


# Limites padrão
DEFAULT_LIMIT = "100/minute"  # 100 requisições por minuto
LOGIN_LIMIT = "5/minute"      # 5 tentativas de login por minuto
ADMIN_LIMIT = "50/minute"     # 50 operações admin por minuto

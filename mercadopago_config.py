"""
Configuração do Mercado Pago
"""
import os
import mercadopago

# Credenciais do Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")

# Inicializar SDK
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# Planos e preços
PLANS = {
    "brasil": {
        "name": "Plano Brasil",
        "description": "Acesso aos ativos brasileiros: WIN, WDO, BIT",
        "price": 97.00,
        "assets": ["WIN", "WDO", "BIT"]
    },
    "global": {
        "name": "Plano Global",
        "description": "Acesso aos ativos globais: BTCUSD, XAUUSD, ES, NAS100, US30, EURUSD, GBPUSD, USDJPY, AUDUSD, WTI",
        "price": 147.00,
        "assets": ["BTCUSD", "XAUUSD", "ES", "NAS100", "US30", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "WTI"]
    },
    "pro": {
        "name": "Plano Pro",
        "description": "Acesso completo a todos os ativos (Brasil + Global)",
        "price": 197.00,
        "assets": ["WIN", "WDO", "BIT", "BTCUSD", "XAUUSD", "ES", "NAS100", "US30", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "WTI"]
    }
}

def get_plan_info(plan_name: str):
    """Retorna informações do plano"""
    return PLANS.get(plan_name)

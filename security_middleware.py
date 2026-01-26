"""
Middleware de Segurança para Atlas Levels
Adiciona cabeçalhos de segurança HTTP e proteções adicionais
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adiciona cabeçalhos de segurança HTTP a todas as respostas
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Proteção contra clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Proteção contra MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Força HTTPS (HSTS) - 1 ano
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Proteção XSS adicional (legacy, mas ainda útil)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Política de referência
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (CSP)
        # Permite scripts inline (necessário para o app atual)
        # Em produção, considere remover 'unsafe-inline' e usar nonces
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Permissions Policy (anteriormente Feature-Policy)
        # Desabilita recursos desnecessários
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        return response

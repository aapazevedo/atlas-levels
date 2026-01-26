"""
Exception Handlers Customizados
Previne vazamento de informações sensíveis em erros
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler customizado para erros de validação
    Remove detalhes técnicos que podem vazar estrutura interna
    """
    
    # Log completo do erro (apenas no servidor)
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    
    # Resposta genérica para o cliente
    # Remove "loc", "type", "ctx" que podem revelar estrutura
    simplified_errors = []
    
    for error in exc.errors():
        field = error.get("loc", [])[-1] if error.get("loc") else "campo"
        msg = error.get("msg", "Valor inválido")
        
        # Mensagens genéricas e seguras
        if "email" in str(field).lower():
            simplified_errors.append({"field": "email", "message": "Email inválido"})
        elif "password" in str(field).lower():
            simplified_errors.append({"field": "password", "message": "Senha inválida ou muito curta"})
        else:
            simplified_errors.append({"field": str(field), "message": "Valor inválido"})
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Dados inválidos", "errors": simplified_errors}
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler genérico para exceções não tratadas
    Previne vazamento de stack traces e detalhes internos
    """
    
    # Log completo do erro (apenas no servidor)
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    
    # Resposta genérica para o cliente
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."}
    )

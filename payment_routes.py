"""
Rotas de pagamento com Mercado Pago
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import mercadopago_config
from database import SessionLocal, get_db
from models import User, Payment
from security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


class CreatePaymentRequest(BaseModel):
    plan: str  # brasil, global, pro
    payment_method: str  # pix, credit_card


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None
    ticket_url: Optional[str] = None


@router.get("/plans")
async def get_plans():
    """Retorna todos os planos disponíveis"""
    return mercadopago_config.PLANS


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Cria um pagamento no Mercado Pago"""
    
    # Validar plano
    plan_info = mercadopago_config.get_plan_info(payment_request.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Plano inválido")
    
    # Criar preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": plan_info["name"],
                "description": plan_info["description"],
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": plan_info["price"]
            }
        ],
        "payer": {
            "email": current_user.email
        },
        "back_urls": {
            "success": "https://atlas-levels-api.onrender.com/app?payment=success",
            "failure": "https://atlas-levels-api.onrender.com/app?payment=failure",
            "pending": "https://atlas-levels-api.onrender.com/app?payment=pending"
        },
        "auto_return": "approved",
        "external_reference": f"{current_user.id}_{payment_request.plan}",
        "notification_url": "https://atlas-levels-api.onrender.com/api/payment/webhook",
        "statement_descriptor": "ATLAS LEVELS",
        "expires": True,
        "expiration_date_from": datetime.now().isoformat(),
        "expiration_date_to": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    # Configurar método de pagamento
    if payment_request.payment_method == "pix":
        preference_data["payment_methods"] = {
            "excluded_payment_methods": [],
            "excluded_payment_types": [
                {"id": "credit_card"},
                {"id": "debit_card"},
                {"id": "ticket"}
            ],
            "installments": 1
        }
    elif payment_request.payment_method == "credit_card":
        preference_data["payment_methods"] = {
            "excluded_payment_methods": [],
            "excluded_payment_types": [
                {"id": "ticket"}
            ],
            "installments": 12
        }
    
    try:
        # Criar preferência no Mercado Pago
        preference_response = mercadopago_config.sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        # Salvar pagamento no banco
        payment = Payment(
            user_id=current_user.id,
            plan=payment_request.plan,
            amount=plan_info["price"],
            payment_method=payment_request.payment_method,
            mp_payment_id=preference["id"],
            status="pending"
        )
        db.add(payment)
        db.commit()
        
        # Retornar resposta
        response = {
            "payment_id": preference["id"],
            "status": "pending",
            "ticket_url": preference["init_point"]
        }
        
        # Se for PIX, incluir QR Code
        if payment_request.payment_method == "pix":
            response["qr_code"] = preference.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
            response["qr_code_base64"] = preference.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao criar pagamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento: {str(e)}")


@router.post("/webhook")
async def payment_webhook(request: Request, db: SessionLocal = Depends(get_db)):
    """Webhook para receber notificações do Mercado Pago"""
    
    try:
        body = await request.json()
        logger.info(f"Webhook recebido: {body}")
        
        # Verificar tipo de notificação
        if body.get("type") == "payment":
            payment_id = body.get("data", {}).get("id")
            
            if payment_id:
                # Buscar informações do pagamento no Mercado Pago
                payment_info = mercadopago_config.sdk.payment().get(payment_id)
                payment_data = payment_info["response"]
                
                # Extrair external_reference (user_id_plan)
                external_ref = payment_data.get("external_reference", "")
                if "_" in external_ref:
                    user_id, plan = external_ref.split("_", 1)
                    
                    # Atualizar status do pagamento no banco
                    payment = db.query(Payment).filter(
                        Payment.user_id == int(user_id),
                        Payment.plan == plan,
                        Payment.mp_payment_id == str(payment_data.get("preference_id", ""))
                    ).first()
                    
                    if payment:
                        payment.status = payment_data.get("status")
                        payment.mp_payment_id = str(payment_id)
                        
                        # Se pagamento aprovado, atualizar plano do usuário
                        if payment_data.get("status") == "approved":
                            user = db.query(User).filter(User.id == int(user_id)).first()
                            if user:
                                user.plan = plan
                                logger.info(f"Plano do usuário {user.email} atualizado para {plan}")
                        
                        db.commit()
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Verifica o status de um pagamento"""
    
    try:
        # Buscar pagamento no banco
        payment = db.query(Payment).filter(
            Payment.user_id == current_user.id,
            Payment.mp_payment_id == payment_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        # Buscar status atualizado no Mercado Pago
        payment_info = mercadopago_config.sdk.payment().get(payment_id)
        payment_data = payment_info["response"]
        
        # Atualizar status no banco
        payment.status = payment_data.get("status")
        db.commit()
        
        return {
            "payment_id": payment_id,
            "status": payment.status,
            "plan": payment.plan,
            "amount": payment.amount
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar status do pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Rotas de pagamento com Mercado Pago
"""
from fastapi import APIRouter, HTTPException, Depends, Request
import hmac
import hashlib
import os
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import mercadopago_config
from database import SessionLocal, get_db
from models import User, Payment
from security import get_current_user
from email_service import send_payment_confirmation_email
import logging
import uuid

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
    
    try:
        # Se for PIX, usar Payment API (gera QR Code direto)
        if payment_request.payment_method == "pix":
            payment_data = {
                "transaction_amount": plan_info["price"],
                "description": plan_info["name"],
                "payment_method_id": "pix",
                "payer": {
                    "email": current_user.email,
                    "first_name": current_user.email.split("@")[0],
                    "last_name": "User"
                },
                "external_reference": f"{current_user.id}_{payment_request.plan}",
                "notification_url": "https://atlas-levels-api.onrender.com/api/payment/webhook"
            }
            
            payment_response = mercadopago_config.sdk.payment().create(payment_data)
            payment_result = payment_response["response"]
            
            # Salvar pagamento no banco
            payment = Payment(
                user_id=current_user.id,
                plan=payment_request.plan,
                amount=plan_info["price"],
                payment_method=payment_request.payment_method,
                mp_payment_id=str(payment_result["id"]),
                status=payment_result.get("status", "pending")
            )
            db.add(payment)
            db.commit()
            
            # Extrair dados do PIX
            qr_code = payment_result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code", "")
            qr_code_base64 = payment_result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64", "")
            
            return PaymentResponse(
                payment_id=str(payment_result["id"]),
                status=payment_result.get("status", "pending"),
                qr_code=qr_code,
                qr_code_base64=qr_code_base64
            )
        
        # Se for cartão, usar Preference API (checkout completo)
        else:
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
                "payment_methods": {
                    "excluded_payment_methods": [],
                    "excluded_payment_types": [
                        {"id": "ticket"}
                    ],
                    "installments": 12
                }
            }
            
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
            
            return PaymentResponse(
                payment_id=preference["id"],
                status="pending",
                ticket_url=preference["init_point"]
            )
        
    except Exception as e:
        logger.error(f"Erro ao criar pagamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento: {str(e)}")


@router.post("/webhook")
async def payment_webhook(request: Request, db: SessionLocal = Depends(get_db)):
    """Webhook para receber notificações do Mercado Pago"""
    
    try:
        body = await request.json()
        logger.info(f"Webhook recebido: {body}")
        
        # SEGURANÇA: Validar assinatura do webhook
        x_signature = request.headers.get("x-signature")
        x_request_id = request.headers.get("x-request-id")
        
        if x_signature and x_request_id:
            # Extrair timestamp e hash da assinatura
            # Formato: "ts=1234567890,v1=abc123..."
            parts = dict(item.split("=") for item in x_signature.split(","))
            ts = parts.get("ts")
            hash_received = parts.get("v1")
            
            # Obter secret do webhook (deve ser configurado como variável de ambiente)
            webhook_secret = os.getenv("MP_WEBHOOK_SECRET", "")
            
            if webhook_secret and ts and hash_received:
                # Construir template de validação
                data_id = body.get("data", {}).get("id", "")
                template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
                
                # Calcular HMAC-SHA256
                hash_calculated = hmac.new(
                    webhook_secret.encode(),
                    template.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                # Comparar assinaturas
                if hash_calculated != hash_received:
                    logger.warning(f"Assinatura do webhook inválida! Possível tentativa de fraude.")
                    return {"status": "error", "message": "Invalid signature"}
                
                logger.info("✅ Assinatura do webhook validada com sucesso")
            else:
                logger.warning("⚠️ Webhook secret não configurado - pulando validação")
        
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
                        Payment.mp_payment_id == str(payment_id)
                    ).first()
                    
                    if payment:
                        payment.status = payment_data.get("status")
                        
                        # Se pagamento aprovado, atualizar plano do usuário
                        if payment_data.get("status") == "approved":
                            # SEGURANÇA: Validar valor pago
                            expected_amount = mercadopago_config.PLANS.get(plan, {}).get("price", 0)
                            actual_amount = payment_data.get("transaction_amount", 0)
                            
                            if abs(expected_amount - actual_amount) > 0.01:
                                logger.error(f"🚨 FRAUDE DETECTADA: Valor divergente! Esperado: R$ {expected_amount}, Recebido: R$ {actual_amount}")
                                payment.status = "fraud_detected"
                                db.commit()
                                return {"status": "error", "message": "Amount mismatch"}
                            
                            user = db.query(User).filter(User.id == int(user_id)).first()
                            if user:
                                user.plan = plan
                                logger.info(f"✅ Plano do usuário {user.email} atualizado para {plan}. Valor: R$ {actual_amount}")
                                
                                # Enviar email de confirmação
                                try:
                                    send_payment_confirmation_email(
                                        to_email=user.email,
                                        plan_name=plan,
                                        plan_price=actual_amount,
                                        payment_method=payment_data.get("payment_type_id", "pix"),
                                        transaction_id=str(payment_id)
                                    )
                                except Exception as e:
                                    logger.error(f"Erro ao enviar email de confirmação: {e}")
                        
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
        try:
            payment_info = mercadopago_config.sdk.payment().get(payment_id)
            payment_data = payment_info["response"]
            
            # Atualizar status no banco
            payment.status = payment_data.get("status")
            
            # Se aprovado, atualizar plano do usuário
            if payment_data.get("status") == "approved":
                current_user.plan = payment.plan
            
            db.commit()
        except:
            # Se falhar ao buscar no MP, usar status do banco
            pass
        
        return {
            "payment_id": payment_id,
            "status": payment.status,
            "plan": payment.plan,
            "amount": payment.amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar status do pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

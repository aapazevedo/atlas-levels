"""
Serviço de envio de emails usando Resend
"""
import os
import resend
from typing import Optional

# Configurar API Key do Resend
resend.api_key = os.getenv("RESEND_API_KEY", "")

# Email remetente (usando domínio de teste do Resend)
FROM_EMAIL = "onboarding@resend.dev"
FROM_NAME = "Atlas Levels"


def send_welcome_email(to_email: str, user_name: Optional[str] = None) -> bool:
    """
    Envia email de boas-vindas após cadastro
    """
    try:
        subject = "🎉 Bem-vindo ao Atlas Levels!"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .features {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .feature-item {{
            margin: 10px 0;
            padding-left: 25px;
            position: relative;
        }}
        .feature-item:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Bem-vindo ao Atlas Levels!</h1>
    </div>
    
    <div class="content">
        <p>Olá{f' {user_name}' if user_name else ''}! 👋</p>
        
        <p>Sua conta foi criada com sucesso! Estamos muito felizes em tê-lo conosco.</p>
        
        <div class="features">
            <h3>🚀 O que você pode fazer agora:</h3>
            <div class="feature-item">Escolher um plano que atende suas necessidades</div>
            <div class="feature-item">Acessar níveis históricos organizados</div>
            <div class="feature-item">Visualizar zonas institucionais</div>
            <div class="feature-item">Operar WIN, WDO, BIT e ativos globais</div>
        </div>
        
        <p><strong>💰 Planos Disponíveis:</strong></p>
        <ul>
            <li><strong>Brasil</strong> - R$ 97/mês (WIN, WDO, BIT)</li>
            <li><strong>Global</strong> - R$ 147/mês (BTCUSD, XAUUSD, ES, NAS100, US30, Forex, WTI)</li>
            <li><strong>Pro</strong> - R$ 197/mês (Todos os ativos)</li>
        </ul>
        
        <center>
            <a href="https://atlas-levels-api.onrender.com/payment" class="button">
                Escolher Meu Plano
            </a>
        </center>
        
        <p>Se tiver qualquer dúvida, estamos aqui para ajudar!</p>
        
        <p>Bons trades! 📈</p>
        
        <p><strong>Equipe Atlas Levels</strong></p>
    </div>
    
    <div class="footer">
        <p>Atlas Levels - Níveis Históricos Organizados</p>
        <p>WIN / WDO / BIT + Global</p>
    </div>
</body>
</html>
        """
        
        params = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Email de boas-vindas enviado para {to_email}: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email de boas-vindas: {e}")
        return False


def send_payment_confirmation_email(
    to_email: str,
    plan_name: str,
    plan_price: float,
    payment_method: str,
    transaction_id: str
) -> bool:
    """
    Envia email de confirmação de pagamento
    """
    try:
        subject = "✅ Pagamento Confirmado - Atlas Levels"
        
        # Mapear nomes dos planos
        plan_names = {
            "brasil": "Brasil",
            "global": "Global",
            "pro": "Pro"
        }
        plan_display = plan_names.get(plan_name.lower(), plan_name)
        
        # Mapear métodos de pagamento
        payment_methods = {
            "pix": "PIX",
            "credit_card": "Cartão de Crédito",
            "debit_card": "Cartão de Débito"
        }
        payment_display = payment_methods.get(payment_method.lower(), payment_method)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .receipt {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #10b981;
        }}
        .receipt-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .receipt-row:last-child {{
            border-bottom: none;
            font-weight: bold;
            font-size: 18px;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .success-icon {{
            font-size: 48px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="success-icon">✅</div>
        <h1>Pagamento Confirmado!</h1>
    </div>
    
    <div class="content">
        <p>Ótimas notícias! Seu pagamento foi processado com sucesso.</p>
        
        <div class="receipt">
            <h3>📄 Detalhes do Pagamento</h3>
            <div class="receipt-row">
                <span>Plano:</span>
                <span><strong>{plan_display}</strong></span>
            </div>
            <div class="receipt-row">
                <span>Método:</span>
                <span>{payment_display}</span>
            </div>
            <div class="receipt-row">
                <span>ID da Transação:</span>
                <span><code>{transaction_id}</code></span>
            </div>
            <div class="receipt-row">
                <span>Valor:</span>
                <span><strong>R$ {plan_price:.2f}</strong></span>
            </div>
        </div>
        
        <p><strong>🎉 Seu acesso foi liberado!</strong></p>
        
        <p>Você agora tem acesso completo aos níveis e zonas institucionais do plano <strong>{plan_display}</strong>.</p>
        
        <center>
            <a href="https://atlas-levels-api.onrender.com/app" class="button">
                Acessar Plataforma
            </a>
        </center>
        
        <p>Se tiver qualquer dúvida sobre seu pagamento ou acesso, entre em contato conosco.</p>
        
        <p>Bons trades! 📈</p>
        
        <p><strong>Equipe Atlas Levels</strong></p>
    </div>
    
    <div class="footer">
        <p>Atlas Levels - Níveis Históricos Organizados</p>
        <p>Este é um email automático, por favor não responda.</p>
    </div>
</body>
</html>
        """
        
        params = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Email de confirmação enviado para {to_email}: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email de confirmação: {e}")
        return False

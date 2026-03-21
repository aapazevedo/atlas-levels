// payment.js - Lógica de pagamento com Mercado Pago

let selectedPlan = null;
let selectedPaymentMethod = null;
let token = localStorage.getItem('access_token') || localStorage.getItem('token');

// Verificar autenticação ao carregar
window.addEventListener('DOMContentLoaded', async () => {
  if (!token) {
    alert('Você precisa fazer login primeiro!');
    window.location.href = '/app';
    return;
  }

  // Carregar informações do usuário
  try {
    const response = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
      const user = await response.json();
      document.getElementById('whoami').textContent = `${user.email} (${user.plan})`;
    } else {
      throw new Error('Não autenticado');
    }
  } catch (error) {
    alert('Sessão expirada. Faça login novamente.');
    window.location.href = '/app';
  }
});

// Voltar ao app
document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = '/app';
});

// Selecionar plano
function selectPlan(plan) {
  selectedPlan = plan;
  
  const plans = {
    'brasil': { name: 'Plano Brasil', price: 'R$ 97/mês' },
    'global': { name: 'Plano Global', price: 'R$ 147/mês' },
    'pro': { name: 'Plano Pro', price: 'R$ 197/mês' }
  };
  
  const planInfo = plans[plan];
  document.getElementById('selectedPlanInfo').innerHTML = 
    `<strong>${planInfo.name}</strong> - ${planInfo.price}`;
  
  // Resetar seleção de método de pagamento
  selectedPaymentMethod = null;
  document.querySelectorAll('.payment-method').forEach(el => {
    el.classList.remove('selected');
  });
  
  // Esconder resultado anterior
  document.getElementById('paymentResult').style.display = 'none';
  document.getElementById('paymentStatus').textContent = '';
  
  // Mostrar modal
  document.getElementById('paymentModal').classList.add('active');
}

// Selecionar método de pagamento
function selectPaymentMethod(method) {
  selectedPaymentMethod = method;
  
  // Atualizar UI
  document.querySelectorAll('.payment-method').forEach(el => {
    el.classList.remove('selected');
  });
  
  document.querySelector(`[data-method="${method}"]`).classList.add('selected');
  
  // Esconder resultado anterior
  document.getElementById('paymentResult').style.display = 'none';
}

// Processar pagamento
async function processPayment() {
  if (!selectedPlan || !selectedPaymentMethod) {
    alert('Selecione um plano e um método de pagamento');
    return;
  }

  const statusEl = document.getElementById('paymentStatus');
  const confirmBtn = document.getElementById('confirmPaymentBtn');
  
  statusEl.textContent = 'Processando pagamento...';
  statusEl.className = 'status';
  confirmBtn.disabled = true;

  try {
    const response = await fetch('/api/payment/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        plan: selectedPlan,
        payment_method: selectedPaymentMethod
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Erro ao criar pagamento');
    }

    // Se for PIX, mostrar QR Code
    if (selectedPaymentMethod === 'pix' && data.qr_code_base64) {
      document.getElementById('qrCodeImage').src = `data:image/png;base64,${data.qr_code_base64}`;
      document.getElementById('pixCode').value = data.qr_code || '';
      document.getElementById('paymentResult').style.display = 'block';
      
      statusEl.textContent = 'QR Code gerado! Escaneie para pagar.';
      statusEl.className = 'status success';
      
      // Iniciar verificação de status
      startPaymentStatusCheck(data.payment_id);
    } 
    // Se for cartão, redirecionar para checkout
    else if (data.ticket_url) {
      statusEl.textContent = 'Redirecionando para pagamento...';
      statusEl.className = 'status success';
      
      setTimeout(() => {
        window.open(data.ticket_url, '_blank');
        statusEl.textContent = 'Complete o pagamento na nova janela';
      }, 1000);
      
      // Iniciar verificação de status
      startPaymentStatusCheck(data.payment_id);
    }

  } catch (error) {
    statusEl.textContent = `Erro: ${error.message}`;
    statusEl.className = 'status error';
  } finally {
    confirmBtn.disabled = false;
  }
}

// Verificar status do pagamento periodicamente
let statusCheckInterval = null;
let pollingStartTime = null;

function startPaymentStatusCheck(paymentId) {
  // Limpar intervalo anterior se existir
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }

  // Registrar tempo de início do polling
  pollingStartTime = Date.now();
  const TIMEOUT = 10 * 60 * 1000; // 10 minutos

  // Verificar a cada 5 segundos
  statusCheckInterval = setInterval(async () => {
    // SEGURANÇA: Verificar timeout
    if (Date.now() - pollingStartTime > TIMEOUT) {
      clearInterval(statusCheckInterval);
      
      document.getElementById('paymentStatus').textContent = 
        '⏱️ Tempo esgotado. Verifique o status do pagamento na sua conta.';
      document.getElementById('paymentStatus').className = 'status error';
      
      // Desabilitar botão de confirmar
      document.getElementById('confirmPaymentBtn').disabled = true;
      return;
    }
    try {
      const response = await fetch(`/api/payment/status/${paymentId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await response.json();

      if (data.status === 'approved') {
        clearInterval(statusCheckInterval);
        
        document.getElementById('paymentStatus').textContent = 
          '✅ Pagamento aprovado! Redirecionando...';
        document.getElementById('paymentStatus').className = 'status success';
        
        setTimeout(() => {
          window.location.href = '/app?payment=success';
        }, 2000);
      } else if (data.status === 'rejected' || data.status === 'cancelled') {
        clearInterval(statusCheckInterval);
        
        document.getElementById('paymentStatus').textContent = 
          '❌ Pagamento não aprovado. Tente novamente.';
        document.getElementById('paymentStatus').className = 'status error';
      }
    } catch (error) {
      console.error('Erro ao verificar status:', error);
    }
  }, 5000);
}

// Copiar código PIX
function copyPixCode() {
  const pixCodeInput = document.getElementById('pixCode');
  pixCodeInput.select();
  document.execCommand('copy');
  
  alert('Código PIX copiado!');
}

// Fechar modal
function closeModal() {
  document.getElementById('paymentModal').classList.remove('active');
  
  // Limpar verificação de status
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
    statusCheckInterval = null;
  }
}

// Fechar modal ao clicar fora
document.getElementById('paymentModal').addEventListener('click', (e) => {
  if (e.target.id === 'paymentModal') {
    closeModal();
  }
});

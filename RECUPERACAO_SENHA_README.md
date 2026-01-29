# Sistema de Recuperação de Senha - Atlas Levels

## 📋 Visão Geral

Sistema completo de recuperação de senha implementado para o SaaS Atlas Levels, incluindo:

- ✅ Endpoints de API para solicitar e confirmar reset de senha
- ✅ Geração de tokens seguros com expiração
- ✅ Envio de emails via Resend
- ✅ Páginas HTML responsivas
- ✅ Migração de banco de dados

---

## 🔧 Componentes Implementados

### 1. Modelo de Dados (`models.py`)

Adicionadas duas novas colunas na tabela `users`:

```python
reset_token = Column(String(255), nullable=True)  # Token para reset de senha
reset_token_expires = Column(DateTime, nullable=True)  # Expiração do token
```

### 2. Endpoints de API (`password_reset_routes.py`)

#### `POST /api/auth/password-reset/request`

Solicita reset de senha. Envia email com link de recuperação.

**Request Body:**
```json
{
  "email": "usuario@example.com"
}
```

**Response:**
```json
{
  "message": "Se o email existir em nossa base, você receberá um link para redefinir sua senha."
}
```

**Segurança:** Sempre retorna sucesso para não vazar informações sobre emails existentes.

#### `POST /api/auth/password-reset/confirm`

Confirma reset de senha com token.

**Request Body:**
```json
{
  "token": "token_seguro_gerado",
  "new_password": "nova_senha_123"
}
```

**Response (Sucesso):**
```json
{
  "message": "Senha redefinida com sucesso! Você já pode fazer login com sua nova senha."
}
```

**Response (Erro):**
```json
{
  "detail": "Token inválido ou expirado"
}
```

### 3. Serviço de Email (`email_service.py`)

#### `send_password_reset_email(to_email, reset_token)`

Envia email com link de recuperação de senha.

**Características:**
- Template HTML profissional
- Link válido por 1 hora
- Avisos de segurança
- Link clicável + texto copiável

### 4. Páginas HTML

#### `/forgot-password` (`forgot-password.html`)

Página para solicitar recuperação de senha.

**Características:**
- Campo de email com validação
- Feedback visual de sucesso/erro
- Loading state durante envio
- Link para voltar ao login

#### `/reset-password?token=XXX` (`reset-password.html`)

Página para redefinir senha com token.

**Características:**
- Validação de token na URL
- Dois campos de senha (confirmação)
- Validação de senha (mínimo 6 caracteres)
- Feedback visual de sucesso/erro
- Redirecionamento automático após sucesso

### 5. Migração de Banco de Dados (`migrate_add_password_reset.py`)

Script para adicionar as novas colunas no banco de dados.

**Compatibilidade:**
- PostgreSQL ✅
- SQLite ✅

**Execução:**
```bash
python migrate_add_password_reset.py
```

---

## 🚀 Como Usar

### Para Usuários

1. **Solicitar Reset:**
   - Acessar: https://atlas-levels-pro.com.br/forgot-password
   - Digitar email cadastrado
   - Clicar em "Enviar Link de Recuperação"
   - Verificar email (inbox + spam)

2. **Redefinir Senha:**
   - Clicar no link recebido por email
   - Digitar nova senha (2x)
   - Clicar em "Redefinir Senha"
   - Fazer login com nova senha

### Para Desenvolvedores

#### Testar Localmente

```bash
# 1. Executar migração
python migrate_add_password_reset.py

# 2. Iniciar servidor
uvicorn main:app --reload

# 3. Testar endpoints
curl -X POST http://localhost:8000/api/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@example.com"}'
```

#### Integrar no Frontend

```javascript
// Solicitar reset
const response = await fetch('/api/auth/password-reset/request', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'usuario@example.com' })
});

// Confirmar reset
const response = await fetch('/api/auth/password-reset/confirm', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    token: 'token_da_url',
    new_password: 'nova_senha'
  })
});
```

---

## 🔒 Segurança

### Tokens

- **Geração:** `secrets.token_urlsafe(32)` (256 bits de entropia)
- **Validade:** 1 hora
- **Uso único:** Token é removido após uso
- **Armazenamento:** Hash não é necessário (token já é aleatório e temporário)

### Proteções

1. **Não vaza informações:** Sempre retorna sucesso ao solicitar reset
2. **Expiração:** Tokens expiram em 1 hora
3. **Uso único:** Token é removido após redefinir senha
4. **Validação:** Senha mínima de 6 caracteres
5. **Rate limiting:** Endpoints protegidos contra brute force

---

## 📧 Configuração de Email

### Resend

O sistema usa Resend para envio de emails. Configure a variável de ambiente:

```bash
RESEND_API_KEY=re_xxxxxxxxxxxxx
```

### Email Remetente

Atualmente configurado como:
```python
FROM_EMAIL = "onboarding@resend.dev"  # Email de teste
```

**Para produção**, alterar para:
```python
FROM_EMAIL = "noreply@send.atlas-levels-pro.com.br"
```

---

## 🧪 Testes

### Teste Manual

1. **Solicitar Reset:**
   ```bash
   curl -X POST https://atlas-levels-pro.com.br/api/auth/password-reset/request \
     -H "Content-Type: application/json" \
     -d '{"email": "seu@email.com"}'
   ```

2. **Verificar Email:**
   - Abrir email recebido
   - Copiar token da URL

3. **Confirmar Reset:**
   ```bash
   curl -X POST https://atlas-levels-pro.com.br/api/auth/password-reset/confirm \
     -H "Content-Type: application/json" \
     -d '{"token": "TOKEN_AQUI", "new_password": "nova_senha_123"}'
   ```

### Teste Automatizado

```python
import requests

# 1. Solicitar reset
response = requests.post(
    'https://atlas-levels-pro.com.br/api/auth/password-reset/request',
    json={'email': 'teste@example.com'}
)
assert response.status_code == 200

# 2. Confirmar reset (com token válido)
response = requests.post(
    'https://atlas-levels-pro.com.br/api/auth/password-reset/confirm',
    json={'token': 'token_valido', 'new_password': 'nova_senha'}
)
assert response.status_code == 200
```

---

## 📝 Próximos Passos (Opcional)

### Melhorias Futuras

1. **Verificação de Email:**
   - Adicionar campo `email_verified` no modelo User
   - Enviar email de confirmação no cadastro
   - Bloquear login até verificar email

2. **Histórico de Senhas:**
   - Impedir reutilização de senhas antigas
   - Armazenar hash das últimas 5 senhas

3. **Autenticação de Dois Fatores (2FA):**
   - Adicionar suporte a TOTP
   - Integrar com Google Authenticator

4. **Notificações de Segurança:**
   - Enviar email ao alterar senha
   - Alertar sobre logins suspeitos

---

## 🐛 Troubleshooting

### Problema: Email não chega

**Solução:**
1. Verificar se `RESEND_API_KEY` está configurada
2. Verificar logs do servidor
3. Verificar pasta de spam
4. Verificar se domínio está verificado no Resend

### Problema: Token inválido ou expirado

**Solução:**
1. Verificar se token está correto na URL
2. Verificar se passou mais de 1 hora
3. Solicitar novo reset

### Problema: Migração falha

**Solução:**
1. Verificar se `DATABASE_URL` está configurada
2. Verificar permissões do banco
3. Executar manualmente:
   ```sql
   ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);
   ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP;
   ```

---

## 📚 Referências

- [Resend Documentation](https://resend.com/docs)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Password Reset](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

---

## ✅ Checklist de Deploy

- [x] Adicionar colunas no modelo User
- [x] Criar endpoints de API
- [x] Implementar envio de email
- [x] Criar páginas HTML
- [x] Adicionar rotas no main.py
- [x] Criar script de migração
- [x] Executar migração local
- [x] Fazer commit e push
- [x] Aguardar deploy no Render
- [ ] Executar migração em produção
- [ ] Testar fluxo completo em produção
- [ ] Atualizar email remetente para domínio customizado

---

**Data de Implementação:** 29 de Janeiro de 2026  
**Desenvolvido por:** Manus AI Assistant  
**Versão:** 1.0.0

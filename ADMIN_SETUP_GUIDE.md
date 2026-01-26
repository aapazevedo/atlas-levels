# Guia de Configuração de Admin - Atlas Levels API

Este guia explica como criar credenciais de administrador para acessar o painel administrativo do **Atlas Levels API** no Render.

---

## 📋 Visão Geral

O projeto **atlas-levels-api** possui um sistema de **bootstrap automático** que cria ou atualiza o usuário admin toda vez que a aplicação inicia. Isso é feito através de variáveis de ambiente configuradas no Render.

---

## ✅ Método 1: Configuração via Variáveis de Ambiente (Recomendado)

Este é o método mais simples e recomendado, pois o admin é criado/atualizado automaticamente sempre que a aplicação reinicia.

### Passos:

1. **Acesse o Dashboard do Render**
   - Vá para: https://dashboard.render.com
   - Selecione seu serviço **atlas-levels-api**

2. **Configure as Variáveis de Ambiente**
   - No menu lateral, clique em **"Environment"**
   - Adicione as seguintes variáveis:

   ```
   BOOTSTRAP_ADMIN_EMAIL=seu-email@exemplo.com
   BOOTSTRAP_ADMIN_PASSWORD=SuaSenhaSegura123!
   BOOTSTRAP_ADMIN_ROLE=admin
   BOOTSTRAP_ADMIN_PLAN=pro
   ```

   **Importante:**
   - `BOOTSTRAP_ADMIN_EMAIL`: Email que você usará para fazer login
   - `BOOTSTRAP_ADMIN_PASSWORD`: Senha forte (máximo 72 caracteres)
   - `BOOTSTRAP_ADMIN_ROLE`: Use `admin` para acesso total
   - `BOOTSTRAP_ADMIN_PLAN`: Opções: `brasil`, `global` ou `pro`

3. **Salve e Reinicie**
   - Clique em **"Save Changes"**
   - O Render reiniciará automaticamente a aplicação
   - Durante o startup, o admin será criado/atualizado automaticamente

4. **Teste o Login**
   - Acesse a URL da sua aplicação: `https://atlas-levels-api.onrender.com/app`
   - Faça login com o email e senha configurados

---

## 🔧 Método 2: Script Manual via Shell do Render

Se você preferir criar o admin manualmente ou se o método automático não funcionar, use este método.

### Passos:

1. **Acesse o Shell do Render**
   - No dashboard do Render, selecione seu serviço **atlas-levels-api**
   - No menu lateral, clique em **"Shell"**
   - Aguarde o shell abrir

2. **Execute o Script de Criação**
   ```bash
   python3 create_admin.py
   ```

3. **Preencha as Informações**
   - O script solicitará:
     - Email do admin
     - Senha do admin
     - Confirmação da senha
     - Role (padrão: admin)
     - Plan (padrão: pro)

4. **Confirme a Criação**
   - Se tudo estiver correto, você verá:
     ```
     ✅ Usuário admin 'seu-email@exemplo.com' criado com sucesso!
        Role: admin
        Plan: pro
     ```

---

## 🔐 Método 3: Criação Rápida via Comando Único

Para criar rapidamente um admin sem interação, você pode usar Python diretamente no shell do Render:

```bash
python3 -c "
import os, sys
sys.path.insert(0, '.')
from database import SessionLocal, Base, engine
from models import User
from security import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()

email = 'admin@atlaslevels.pro'
password = 'SuaSenhaSegura123!'

try:
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.password_hash = get_password_hash(password)
        user.role = 'admin'
        user.plan = 'pro'
        db.commit()
        print(f'✅ Admin {email} atualizado!')
    else:
        new_user = User(
            email=email,
            password_hash=get_password_hash(password),
            role='admin',
            plan='pro'
        )
        db.add(new_user)
        db.commit()
        print(f'✅ Admin {email} criado!')
except Exception as e:
    print(f'❌ Erro: {e}')
    db.rollback()
finally:
    db.close()
"
```

**Importante:** Substitua `admin@atlaslevels.pro` e `SuaSenhaSegura123!` pelos valores desejados.

---

## 📊 Verificação do Banco de Dados

Para verificar se o admin foi criado corretamente, você pode consultar o banco PostgreSQL:

### Via Shell do Render:

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from models import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print('Usuários no banco:')
    for u in users:
        print(f'  - {u.email} | Role: {u.role} | Plan: {u.plan}')
finally:
    db.close()
"
```

---

## 🎯 Estrutura de Planos

O Atlas Levels possui três planos diferentes:

| Plano | Ativos Disponíveis |
|-------|-------------------|
| **brasil** | WIN, WDO, BIT |
| **global** | BTCUSD, XAUUSD, ES, NAS100, US30, EURUSD, GBPUSD, USDJPY, AUDUSD, WTI |
| **pro** | Todos os ativos (Brasil + Global) |

---

## 🔒 Segurança

### Boas Práticas:

1. **Senha Forte**: Use senhas com pelo menos 12 caracteres, incluindo letras maiúsculas, minúsculas, números e símbolos
2. **Limite de 72 Bytes**: O bcrypt tem limite de 72 bytes. O sistema trunca automaticamente senhas maiores
3. **Não Compartilhe**: Mantenha as credenciais de admin em segredo
4. **Variáveis de Ambiente**: Nunca commite senhas no código. Use sempre variáveis de ambiente

### Exemplo de Senha Forte:
```
AtLas#2026$Levels!Pro
```

---

## 🐛 Troubleshooting

### Problema: Admin não foi criado após reiniciar

**Solução:**
1. Verifique se as variáveis de ambiente estão corretas
2. Verifique os logs do Render para mensagens de erro
3. Tente criar manualmente usando o Método 2 ou 3

### Problema: Erro "Credenciais inválidas" ao fazer login

**Solução:**
1. Verifique se o email está em minúsculas
2. Confirme que a senha está correta (sem espaços extras)
3. Recrie o admin usando o script manual

### Problema: Senha muito longa

**Solução:**
- O bcrypt aceita no máximo 72 bytes
- Use uma senha com até 72 caracteres ASCII
- O sistema trunca automaticamente senhas maiores

---

## 📞 Suporte

Para mais informações sobre o projeto:
- **Repositório**: https://github.com/aapazevedo/atlas-levels
- **Render Dashboard**: https://dashboard.render.com

---

## 📝 Notas Técnicas

### Como Funciona o Bootstrap Automático:

O arquivo `main.py` contém uma função `bootstrap_admin()` que é executada no evento `startup` do FastAPI:

```python
@app.on_event("startup")
def bootstrap_admin():
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "admin@atlaslevels.pro"
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "admin123"
    role = os.getenv("BOOTSTRAP_ADMIN_ROLE") or "admin"
    plan = os.getenv("BOOTSTRAP_ADMIN_PLAN") or "pro"
    
    # Cria ou atualiza o usuário admin no banco
    # ...
```

Esta função:
1. Lê as variáveis de ambiente
2. Valida os valores (role e plan)
3. Protege contra senhas muito longas (>72 bytes)
4. Cria ou atualiza o usuário admin no banco PostgreSQL
5. Registra mensagens de sucesso/erro nos logs

---

**Última atualização**: Janeiro 2026

# Atlas Levels — Institutional Zones (MVP rodando)

Este MVP entrega:
- Login com JWT
- API de níveis (protege o seu método: só expõe valores finais)
- Painel web simples (HTML) servido pelo próprio FastAPI
- Endpoint admin para inserir níveis
- Banco SQLite local (fácil de rodar). Troca para PostgreSQL depois.

## 1) Rodar local (Windows/Mac/Linux)

Abra um terminal dentro da pasta `backend`:

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Crie seu `.env`:
```bash
copy .env.example .env   # Windows
# ou
cp .env.example .env     # Mac/Linux
```

Edite o `.env` e troque `JWT_SECRET`.

## 2) Criar banco + usuário admin + dados de exemplo

```bash
python seed_data.py
```

Isso cria:
- Usuário admin: `admin@atlaslevels.pro` / senha: `admin123`
- Usuário cliente (demo): `demo@atlaslevels.pro` / senha: `demo123`
- Alguns níveis de exemplo para WIN/WDO/BIT e mercados globais

## 3) Subir o servidor

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Acesse:
- Painel: http://127.0.0.1:8000
- Docs da API: http://127.0.0.1:8000/docs

## 4) Inserir/atualizar níveis (admin)

No painel, faça login como admin e use a aba “Admin”.

Ou via API:
- POST /api/admin/levels (Bearer token admin)

## 5) Próximo passo (produção)
- Trocar SQLite por PostgreSQL (mesmo código, só muda DB_URL)
- Colocar Stripe/Kiwify e controle de planos
- Hospedar em VPS (Fly.io/Hetzner/Oracle)

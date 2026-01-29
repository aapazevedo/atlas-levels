"""
Script de migração para adicionar colunas de verificação de email
"""
import os
from sqlalchemy import create_engine, text

# Obter URL do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL não configurada!")
    exit(1)

# Criar engine
engine = create_engine(DATABASE_URL)

print("🔧 Iniciando migração: Adicionar colunas de verificação de email")

try:
    with engine.connect() as conn:
        # Adicionar coluna email_verified
        print("📝 Adicionando coluna email_verified...")
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS email_verified INTEGER DEFAULT 0 NOT NULL
        """))
        conn.commit()
        print("✅ Coluna email_verified adicionada")
        
        # Adicionar coluna verification_token
        print("📝 Adicionando coluna verification_token...")
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255)
        """))
        conn.commit()
        print("✅ Coluna verification_token adicionada")
        
    print("🎉 Migração concluída com sucesso!")
    
except Exception as e:
    print(f"❌ Erro na migração: {e}")
    exit(1)

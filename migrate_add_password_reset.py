"""
Script de migração para adicionar colunas de reset de senha
"""
import os
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def migrate():
    """Adiciona colunas reset_token e reset_token_expires na tabela users"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Verificar se as colunas já existem
            if 'postgresql' in DATABASE_URL or 'postgres' in DATABASE_URL:
                # PostgreSQL
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='reset_token'
                """))
                
                if result.fetchone() is None:
                    print("📝 Adicionando coluna reset_token...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
                    conn.commit()
                    print("✅ Coluna reset_token adicionada")
                else:
                    print("ℹ️ Coluna reset_token já existe")
                
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='reset_token_expires'
                """))
                
                if result.fetchone() is None:
                    print("📝 Adicionando coluna reset_token_expires...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP"))
                    conn.commit()
                    print("✅ Coluna reset_token_expires adicionada")
                else:
                    print("ℹ️ Coluna reset_token_expires já existe")
                    
            else:
                # SQLite
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'reset_token' not in columns:
                    print("📝 Adicionando coluna reset_token...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
                    conn.commit()
                    print("✅ Coluna reset_token adicionada")
                else:
                    print("ℹ️ Coluna reset_token já existe")
                
                if 'reset_token_expires' not in columns:
                    print("📝 Adicionando coluna reset_token_expires...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
                    conn.commit()
                    print("✅ Coluna reset_token_expires adicionada")
                else:
                    print("ℹ️ Coluna reset_token_expires já existe")
            
            print("\n🎉 Migração concluída com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()

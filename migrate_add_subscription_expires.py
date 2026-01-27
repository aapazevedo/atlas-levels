"""
Migração: Adicionar coluna subscription_expires à tabela users
Data: 2026-01-27
"""

import sqlite3
from datetime import datetime, timedelta

def migrate():
    conn = sqlite3.connect('atlas_levels.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'subscription_expires' in columns:
            print("✅ Coluna 'subscription_expires' já existe. Migração não necessária.")
            return
        
        print("📝 Adicionando coluna 'subscription_expires' à tabela users...")
        
        # Adicionar coluna
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN subscription_expires DATETIME
        """)
        
        # Definir vencimento padrão para usuários existentes (30 dias a partir de hoje)
        default_expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        cursor.execute("""
            UPDATE users 
            SET subscription_expires = ? 
            WHERE subscription_expires IS NULL
        """, (default_expires,))
        
        conn.commit()
        
        # Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_expires IS NOT NULL")
        count = cursor.fetchone()[0]
        
        print(f"✅ Migração concluída com sucesso!")
        print(f"   - Coluna 'subscription_expires' adicionada")
        print(f"   - {count} usuários atualizados com vencimento padrão (30 dias)")
        print(f"   - Vencimento padrão: {default_expires}")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

-- Script SQL para adicionar colunas de reset de senha
-- Execute este comando no Shell do Render

ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;

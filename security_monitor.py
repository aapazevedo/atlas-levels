"""
Sistema de Monitoramento de Segurança
Detecta comportamentos suspeitos e padrões anormais
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Monitora comportamento suspeito de usuários/IPs
    """
    
    def __init__(self):
        # Armazena tentativas de login falhadas por IP
        self.failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        
        # Armazena requisições por IP
        self.requests_per_ip: Dict[str, List[datetime]] = defaultdict(list)
        
        # IPs bloqueados temporariamente
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Tempo de bloqueio (em minutos)
        self.block_duration = 30
        
        # Limites para detecção
        self.max_failed_logins = 10  # 10 falhas em 10 minutos
        self.failed_login_window = 10  # minutos
        
        self.max_requests = 500  # 500 requisições em 5 minutos
        self.request_window = 5  # minutos
    
    def record_failed_login(self, ip: str, email: str = None):
        """
        Registra tentativa de login falhada
        """
        now = datetime.now()
        self.failed_logins[ip].append(now)
        
        # Limpar registros antigos
        cutoff = now - timedelta(minutes=self.failed_login_window)
        self.failed_logins[ip] = [t for t in self.failed_logins[ip] if t > cutoff]
        
        # Verificar se deve bloquear
        if len(self.failed_logins[ip]) >= self.max_failed_logins:
            self.block_ip(ip, reason="Múltiplas tentativas de login falhadas")
            logger.warning(f"🚨 IP {ip} bloqueado por {self.max_failed_logins} tentativas de login falhadas")
            if email:
                logger.warning(f"   Tentando acessar: {email}")
    
    def record_request(self, ip: str, path: str):
        """
        Registra requisição
        """
        now = datetime.now()
        self.requests_per_ip[ip].append(now)
        
        # Limpar registros antigos
        cutoff = now - timedelta(minutes=self.request_window)
        self.requests_per_ip[ip] = [t for t in self.requests_per_ip[ip] if t > cutoff]
        
        # Verificar comportamento suspeito
        if len(self.requests_per_ip[ip]) >= self.max_requests:
            self.block_ip(ip, reason="Volume excessivo de requisições")
            logger.warning(f"🚨 IP {ip} bloqueado por volume excessivo: {len(self.requests_per_ip[ip])} requisições em {self.request_window} minutos")
            logger.warning(f"   Última requisição: {path}")
    
    def block_ip(self, ip: str, reason: str):
        """
        Bloqueia IP temporariamente
        """
        self.blocked_ips[ip] = datetime.now() + timedelta(minutes=self.block_duration)
        logger.warning(f"🚫 IP {ip} bloqueado por {self.block_duration} minutos. Razão: {reason}")
    
    def is_blocked(self, ip: str) -> bool:
        """
        Verifica se IP está bloqueado
        """
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                # Bloqueio expirou
                del self.blocked_ips[ip]
                logger.info(f"✅ Bloqueio de {ip} expirou")
        return False
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas de segurança
        """
        return {
            "blocked_ips": len(self.blocked_ips),
            "monitored_ips": len(self.requests_per_ip),
            "failed_login_attempts": sum(len(attempts) for attempts in self.failed_logins.values())
        }


# Instância global do monitor
security_monitor = SecurityMonitor()

"""
Utilitário para carregar credenciais de banco de dados a partir dos arquivos em .security.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from app.config.settings import SECURITY_DIR
from app.config.encrypted_settings import encrypted_settings

# Configuração de logging
logger = logging.getLogger(__name__)

class CredentialsLoader:
    """
    Classe para carregar credenciais de banco de dados a partir dos arquivos em .security.
    """
    
    @staticmethod
    def load_credentials(is_local: bool = True) -> Dict[str, str]:
        """
        Carrega credenciais de banco de dados a partir dos arquivos em .security.
        
        Args:
            is_local: Se True, carrega credenciais do banco local, caso contrário do remoto
            
        Returns:
            Dict[str, str]: Dicionário com as credenciais
        """
        try:
            # Determinar o diretório de segurança
            security_dir = SECURITY_DIR / ('mysql_local' if is_local else 'mysql_remoto')
            
            # Verificar se o diretório existe
            if not security_dir.exists():
                logger.error(f"Diretório de segurança não encontrado: {security_dir}")
                return {}
                
            # Configurar o encrypted_settings para usar o diretório correto
            original_security_dir = encrypted_settings.key_file.parent
            encrypted_settings.key_file = security_dir / 'crypto.key'
            encrypted_settings.env_file = security_dir / '.env.encrypted'
            
            # Carregar configurações
            try:
                # Obter credenciais do arquivo criptografado
                db_host = encrypted_settings.get('DB_HOST') or encrypted_settings.get('MYSQL_HOST')
                db_user = encrypted_settings.get('DB_USER') or encrypted_settings.get('MYSQL_USER')
                db_password = encrypted_settings.get('DB_PASSWORD') or encrypted_settings.get('MYSQL_PASSWORD')
                db_name = encrypted_settings.get('DB_NAME') or encrypted_settings.get('MYSQL_DATABASE')
                db_port = encrypted_settings.get('DB_PORT') or encrypted_settings.get('MYSQL_PORT', '3306')
                
                # Restaurar configuração original
                encrypted_settings.key_file = original_security_dir / 'crypto.key'
                encrypted_settings.env_file = original_security_dir / '.env.encrypted'
                
                # Verificar se as credenciais estão completas
                if not db_host or not db_user or not db_password or not db_name:
                    logger.error(f"Credenciais incompletas para {'local' if is_local else 'remoto'}")
                    return {}
                    
                # Retornar credenciais
                return {
                    'host': db_host,
                    'port': db_port,
                    'user': db_user,
                    'password': db_password,
                    'database': db_name
                }
                
            except Exception as e:
                logger.error(f"Erro ao carregar credenciais: {e}")
                # Restaurar configuração original
                encrypted_settings.key_file = original_security_dir / 'crypto.key'
                encrypted_settings.env_file = original_security_dir / '.env.encrypted'
                return {}
                
        except Exception as e:
            logger.error(f"Erro ao carregar credenciais: {e}")
            return {}
            
    @staticmethod
    def setup_environment_variables():
        """
        Configura variáveis de ambiente com as credenciais de banco de dados.
        """
        try:
            # Carregar credenciais
            local_credentials = CredentialsLoader.load_credentials(is_local=True)
            remote_credentials = CredentialsLoader.load_credentials(is_local=False)
            
            # Configurar variáveis de ambiente para MySQL local
            if local_credentials:
                os.environ['MYSQL_LOCAL_HOST'] = local_credentials.get('host', 'localhost')
                os.environ['MYSQL_LOCAL_PORT'] = local_credentials.get('port', '3306')
                os.environ['MYSQL_LOCAL_USER'] = local_credentials.get('user', 'root')
                os.environ['MYSQL_LOCAL_PASSWORD'] = local_credentials.get('password', '')
                os.environ['MYSQL_LOCAL_DATABASE'] = local_credentials.get('database', 'controlix_local')
                logger.info(f"Credenciais locais configuradas: {local_credentials.get('host')}")
            
            # Configurar variáveis de ambiente para MySQL remoto
            if remote_credentials:
                os.environ['MYSQL_REMOTE_HOST'] = remote_credentials.get('host', '')
                os.environ['MYSQL_REMOTE_PORT'] = remote_credentials.get('port', '3306')
                os.environ['MYSQL_REMOTE_USER'] = remote_credentials.get('user', '')
                os.environ['MYSQL_REMOTE_PASSWORD'] = remote_credentials.get('password', '')
                os.environ['MYSQL_REMOTE_DATABASE'] = remote_credentials.get('database', 'controlix_remote')
                logger.info(f"Credenciais remotas configuradas: {remote_credentials.get('host')}")
                
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar variáveis de ambiente: {e}")
            return False
            
    @staticmethod
    def test_connection(is_local: bool = True) -> Tuple[bool, str]:
        """
        Testa a conexão com o banco de dados.
        
        Args:
            is_local: Se True, testa a conexão com o banco local, caso contrário com o remoto
            
        Returns:
            Tuple[bool, str]: Tupla com status da conexão e mensagem
        """
        try:
            import mysql.connector
            
            # Carregar credenciais
            credentials = CredentialsLoader.load_credentials(is_local)
            
            if not credentials:
                return False, "Credenciais não encontradas"
                
            # Tentar conectar
            connection = mysql.connector.connect(
                host=credentials['host'],
                port=int(credentials['port']),
                user=credentials['user'],
                password=credentials['password'],
                database=credentials['database'],
                connection_timeout=5
            )
            
            if connection.is_connected():
                # Obter informações do servidor
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                cursor.close()
                connection.close()
                
                return True, f"Conexão bem-sucedida. Versão do servidor: {version}"
            else:
                return False, "Falha na conexão"
                
        except Exception as e:
            return False, f"Erro ao testar conexão: {e}"

# Carregar credenciais ao importar o módulo
credentials_loader = CredentialsLoader() 
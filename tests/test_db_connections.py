import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao path para importações
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Importações do sistema
from app.config.encrypted_settings import EncryptedSettings, ConfigError
from app.config.settings import SECURITY_DIR, MYSQL_LOCAL_DIR, MYSQL_REMOTE_DIR
from app.data.connection import DatabaseConnection

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/db_connection_test.log')
    ]
)

logger = logging.getLogger('db_connection_test')

def test_local_connection():
    """Testa a conexão com o banco de dados local"""
    logger.info("=== TESTE DE CONEXÃO COM BANCO DE DADOS LOCAL ===")
    
    try:
        # Carrega as configurações criptografadas
        logger.info("Carregando configurações criptografadas locais...")
        local_settings = EncryptedSettings(MYSQL_LOCAL_DIR)
        
        # Tenta descriptografar
        config = local_settings.decrypt_env()
        logger.info(f"Configurações locais encontradas: {', '.join(config.keys())}")
        
        # Log de informações (sem senha)
        safe_config = {k: v if 'PASSWORD' not in k.upper() else '***' for k, v in config.items()}
        logger.info(f"Configurações do banco local: {safe_config}")
        
        # Inicializa a conexão
        logger.info("Inicializando conexão com banco de dados local...")
        db = DatabaseConnection()
        
        # Tenta obter uma conexão
        logger.info("Tentando obter conexão com banco de dados local...")
        connection = db.get_connection(is_local=True)
        
        # Testa a conexão com uma consulta simples
        logger.info("Testando conexão com uma consulta simples...")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Verifica o resultado
        if result and result[0] == 1:
            logger.info("✅ Conexão com banco de dados local estabelecida com sucesso!")
        else:
            logger.error("❌ Teste de conexão local falhou: resultado inesperado.")
        
        # Libera a conexão
        db.release_connection(connection)
        logger.info("Conexão liberada.")
        
    except ConfigError as ce:
        logger.error(f"❌ Erro de configuração: {ce}")
        print(f"\nERRO DE CONFIGURAÇÃO: {ce}")
        print("Verifique se os arquivos de configuração estão presentes em .security/mysql_local/")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com banco de dados local: {e}", exc_info=True)
        print(f"\nERRO: {e}")

def test_remote_connection():
    """Testa a conexão com o banco de dados remoto"""
    logger.info("=== TESTE DE CONEXÃO COM BANCO DE DADOS REMOTO ===")
    
    try:
        # Carrega as configurações criptografadas
        logger.info("Carregando configurações criptografadas remotas...")
        remote_settings = EncryptedSettings(MYSQL_REMOTE_DIR)
        
        # Tenta descriptografar
        config = remote_settings.decrypt_env()
        logger.info(f"Configurações remotas encontradas: {', '.join(config.keys())}")
        
        # Log de informações (sem senha)
        safe_config = {k: v if 'PASSWORD' not in k.upper() else '***' for k, v in config.items()}
        logger.info(f"Configurações do banco remoto: {safe_config}")
        
        # Inicializa a conexão
        logger.info("Inicializando conexão com banco de dados remoto...")
        db = DatabaseConnection()
        
        # Tenta obter uma conexão
        logger.info("Tentando obter conexão com banco de dados remoto...")
        connection = db.get_connection(is_local=False)
        
        # Testa a conexão com uma consulta simples
        logger.info("Testando conexão com uma consulta simples...")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Verifica o resultado
        if result and result[0] == 1:
            logger.info("✅ Conexão com banco de dados remoto estabelecida com sucesso!")
        else:
            logger.error("❌ Teste de conexão remoto falhou: resultado inesperado.")
        
        # Libera a conexão
        db.release_connection(connection)
        logger.info("Conexão liberada.")
        
    except ConfigError as ce:
        logger.error(f"❌ Erro de configuração: {ce}")
        print(f"\nERRO DE CONFIGURAÇÃO: {ce}")
        print("Verifique se os arquivos de configuração estão presentes em .security/mysql_remoto/")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com banco de dados remoto: {e}", exc_info=True)
        print(f"\nERRO: {e}")

def create_connection_settings():
    """Cria ou atualiza os arquivos de configuração para conexão"""
    # Esta função pode ser implementada se necessário criar novas configurações
    # mas como você mencionou que deseja usar os arquivos existentes, não a implementarei aqui
    pass

if __name__ == "__main__":
    print("\n=== TESTE DE CONEXÃO COM BANCOS DE DADOS ===\n")
    
    # Teste de conexão local
    print("Testando conexão com banco de dados LOCAL...")
    test_local_connection()
    
    print("\n" + "-" * 60 + "\n")
    
    # Teste de conexão remota
    print("Testando conexão com banco de dados REMOTO...")
    test_remote_connection()
    
    print("\n" + "=" * 60)
    print("Logs detalhados disponíveis em logs/db_connection_test.log") 
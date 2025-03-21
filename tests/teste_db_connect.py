import sys
import os
import logging

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.connection import db
from app.config.encrypted_settings import EncryptedSettings

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,  # Mudado para DEBUG para ver mais informações
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_connection():
    """Testa a conexão com o banco de dados"""
    try:
        # Primeiro, vamos verificar as configurações
        logger.info("Verificando configurações...")
        settings = EncryptedSettings()
        config = settings.decrypt_env()
        logger.info(f"Configurações encontradas: {', '.join(config.keys())}")
        
        # Tenta obter conexão
        logger.info("Tentando estabelecer conexão...")
        conn = db.get_connection()
        
        if conn:
            db_type = "MySQL" if db.is_mysql_available else "SQLite"
            logger.info(f"Conexão estabelecida com sucesso usando {db_type}")
            
            # Testa uma query simples
            try:
                result = db.execute_query("SELECT 1 as test")
                logger.info(f"Resultado da query: {result}")
                
                if result is not None:
                    logger.info("Query de teste executada com sucesso")
                else:
                    logger.error("Query de teste falhou")
                    
            except Exception as e:
                logger.error(f"Erro ao executar query de teste: {e}", exc_info=True)
            finally:
                if db.is_mysql_available and conn:
                    conn.close()  # Retorna a conexão para o pool
        else:
            logger.error("Não foi possível estabelecer conexão com nenhum banco de dados")
            logger.debug(f"Status MySQL: {db.is_mysql_available}")
            logger.debug(f"Pool MySQL: {db.mysql_pool is not None}")
            logger.debug(f"SQLite: {db.sqlite_conn is not None}")
            
    except Exception as e:
        logger.error(f"Erro durante teste de conexão: {e}", exc_info=True)
    finally:
        logger.info("Teste de conexão concluído")

if __name__ == "__main__":
    logger.info("Iniciando teste de conexão com banco de dados...")
    test_connection()

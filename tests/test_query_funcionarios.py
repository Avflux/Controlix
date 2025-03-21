import sys
import os
import logging
from pathlib import Path
import mysql.connector
from datetime import datetime

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.encrypted_settings import EncryptedSettings
from app.data.connection import DatabaseConnection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/database.log'
)
logger = logging.getLogger(__name__)

def test_query_funcionarios():
    """Testa consulta à tabela funcionarios"""
    try:
        logger.info("Iniciando teste de consulta à tabela funcionarios")
        
        # Inicializa conexões
        settings = EncryptedSettings()
        db = DatabaseConnection()
        
        # Verifica se MySQL está disponível
        if not db.is_mysql_available:
            logger.error("MySQL não está disponível")
            return
        
        # Query para selecionar funcionários
        query = """
            SELECT 
                id,
                name_id,
                senha,
                nome,
                email,
                status
            FROM funcionarios
            ORDER BY id
        """
        
        # Executa a query
        results = db.execute_query(query)
        
        # Exibe resultados
        logger.info(f"Total de funcionários encontrados: {len(results)}")
        for funcionario in results:
            logger.info("-" * 50)
            logger.info(f"ID: {funcionario['id']}")
            logger.info(f"Name ID: {funcionario['name_id']}")
            logger.info(f"Nome: {funcionario['nome']}")
            logger.info(f"Email: {funcionario['email']}")
            logger.info(f"Status: {funcionario['status']}")
            # Não exibe a senha por segurança
        
        logger.info("Consulta realizada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao consultar funcionários: {e}")
        return False

def main():
    """Função principal"""
    try:
        # Executa o teste
        success = test_query_funcionarios()
        
        if success:
            print("✓ Teste concluído com sucesso")
            logger.info("Teste concluído com sucesso")
        else:
            print("✗ Teste falhou")
            logger.error("Teste falhou")
            
    except Exception as e:
        print(f"✗ Erro no teste: {e}")
        logger.error(f"Erro no teste: {e}")

if __name__ == "__main__":
    main() 
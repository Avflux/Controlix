import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.connection import db
from app.config.encrypted_settings import EncryptedSettings, ConfigError
from tkinter import messagebox

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_sqlite_fallback():
    """Testa o funcionamento do SQLite como fallback quando não há credenciais MySQL"""
    try:
        logger.info("Iniciando teste de fallback SQLite...")
        
        # Verifica se há conexão
        if not db.current_connection:
            raise Exception("Nenhuma conexão de banco de dados disponível")
            
        # Identifica qual banco está sendo usado
        db_type = "MySQL" if db.is_mysql_available else "SQLite"
        logger.info(f"Usando {db_type} como banco de dados")
        
        # Testa query simples
        result = db.execute_query("SELECT 1 as test")
        if not result or result[0]['test'] != 1:
            raise Exception("Query de teste falhou")
            
        # Testa operações básicas
        try:
            # Cria tabela de teste se não existir
            db.execute_query("""
                CREATE TABLE IF NOT EXISTS test_fallback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            
            # INSERT
            db.execute_query(
                "INSERT INTO test_fallback (name) VALUES (?)",
                ("teste",)
            )
            
            # SELECT
            result = db.execute_query("SELECT * FROM test_fallback")
            if not result:
                raise Exception("Não foi possível recuperar dados inseridos")
                
            # UPDATE
            db.execute_query(
                "UPDATE test_fallback SET name = ? WHERE name = ?",
                ("teste_atualizado", "teste")
            )
            
            # DELETE
            db.execute_query("DELETE FROM test_fallback")
            
            logger.info("Operações básicas realizadas com sucesso")
            
        finally:
            # Limpa tabela de teste
            try:
                db.execute_query("DROP TABLE IF EXISTS test_fallback")
            except:
                pass
        
        logger.info("Teste de fallback concluído com sucesso!")
        messagebox.showinfo(
            "Teste SQLite",
            f"Sistema funcionando corretamente usando {db_type}\n"
            "Todas as operações básicas foram realizadas com sucesso."
        )
        
    except Exception as e:
        logger.error(f"Erro durante teste de fallback: {e}", exc_info=True)
        messagebox.showerror(
            "Erro no Teste",
            f"Falha ao testar sistema: {str(e)}\n"
            "Verifique os logs para mais detalhes."
        )

if __name__ == "__main__":
    test_sqlite_fallback() 
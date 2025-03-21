import sys
from pathlib import Path
import time
from datetime import datetime, timedelta

# Adiciona diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

import logging
from app.data.connection import db
from app.data.cache.query_cache import query_cache

logger = logging.getLogger(__name__)

class DatabaseTester:
    def __init__(self):
        self.test_data = {
            'funcionarios': [
                {
                    'name_id': 'test_user1',
                    'senha': 'test123',
                    'status': 1
                },
                {
                    'name_id': 'test_user2',
                    'senha': 'test456',
                    'status': 1
                }
            ]
        }
        
    def run_all_tests(self):
        """Executa todos os testes"""
        logger.info("Iniciando testes de banco de dados...")
        
        tests = [
            self.test_mysql_connection,
            self.test_sqlite_fallback,
            self.test_crud_operations,
            self.test_cache,
            self.test_transaction
        ]
        
        results = []
        for test in tests:
            try:
                test()
                results.append(f"✅ {test.__name__} passou")
            except Exception as e:
                results.append(f"❌ {test.__name__} falhou: {str(e)}")
                logger.error(f"Erro em {test.__name__}: {e}", exc_info=True)
                
        return results
        
    def test_mysql_connection(self):
        """Testa conexão MySQL"""
        # Força usar MySQL
        if not db.is_mysql_available:
            raise Exception("MySQL não está disponível")
            
        # Testa query simples
        result = db.execute_query("SELECT 1")
        if not result:
            raise Exception("Query MySQL falhou")
            
        logger.info("Teste de conexão MySQL passou")
        
    def test_sqlite_fallback(self):
        """Testa fallback para SQLite"""
        # Força desconexão MySQL temporariamente
        original_mysql = db.mysql_pool
        original_mysql_conn = db.mysql_conn
        db.mysql_pool = None
        db.mysql_conn = None
        db.is_mysql_available = False  # Força usar SQLite
        
        try:
            # Deve usar SQLite automaticamente
            result = db.execute_query("SELECT 1 as test")
            if not result or not result[0]['test'] == 1:
                raise Exception("Fallback SQLite falhou")
                
            logger.info("Teste de fallback SQLite passou")
            
        finally:
            # Restaura MySQL
            db.mysql_pool = original_mysql
            db.mysql_conn = original_mysql_conn
            db.is_mysql_available = True
            
    def test_crud_operations(self):
        """Testa operações CRUD"""
        try:
            # Verifica estrutura primeiro
            if not self.test_table_structure():
                raise Exception("Estrutura da tabela não está correta")
            
            # Limpa dados de teste anteriores
            db.execute_query("DELETE FROM funcionarios WHERE name_id = 'test_crud'")
            
            # Conta registros antes
            before_count = db.execute_query(
                "SELECT COUNT(*) as count FROM funcionarios",
                fetch_one=True
            )
            
            # Tenta INSERT com parâmetros
            logger.debug("Tentando inserir usuário de teste...")
            try:
                params = {
                    'nome': 'Usuário Teste',
                    'email': 'teste@teste.com',
                    'name_id': 'test_crud',
                    'senha': 'test789',
                    'status': 1
                }
                
                insert_query = """
                    INSERT INTO funcionarios 
                        (nome, email, name_id, senha, status) 
                    VALUES 
                        (%(nome)s, %(email)s, %(name_id)s, %(senha)s, %(status)s)
                """
                
                # Executa INSERT
                insert_id = db.execute_query(insert_query, params)
                
                # Verifica se inseriu
                if not insert_id:
                    # Tenta buscar pelo name_id já que o ID não foi retornado
                    check = db.execute_query(
                        "SELECT * FROM funcionarios WHERE name_id = %(name_id)s",
                        {'name_id': 'test_crud'},
                        fetch_one=True
                    )
                    
                    if not check:
                        raise Exception("INSERT falhou - registro não encontrado")
                    insert_id = check['id']
                
                logger.info(f"Registro inserido com sucesso. ID: {insert_id}")
                
                # Verifica contagem
                count = db.execute_query(
                    "SELECT COUNT(*) as total FROM funcionarios",
                    fetch_one=True
                )
                logger.info(f"Total de registros: {count['total']}")
                
            except Exception as e:
                logger.error(f"Erro detalhado no INSERT: {str(e)}", exc_info=True)
                # Verifica estado da conexão
                try:
                    ping_result = db.execute_query("SELECT 1")
                    logger.debug(f"Conexão ainda ativa: {ping_result}")
                except:
                    logger.error("Conexão perdida após erro")
                raise
            
            # READ com mais detalhes
            logger.debug("Tentando ler usuário inserido...")
            user = db.execute_query("""
                SELECT id, name_id, senha, status, created_at, updated_at
                FROM funcionarios 
                WHERE name_id = %s
            """, ('test_crud',), fetch_one=True)
            logger.debug(f"Dados completos do usuário: {user}")
            
            if not user:
                raise Exception("Usuário não encontrado após INSERT")
            if user['name_id'] != 'test_crud':
                raise Exception(f"name_id incorreto: {user['name_id']}")
                
            # UPDATE
            logger.debug("Tentando atualizar status do usuário...")
            update_result = db.execute_query(
                "UPDATE funcionarios SET status = %s WHERE name_id = %s",
                (0, 'test_crud')
            )
            logger.debug(f"Resultado do UPDATE: {update_result}")
            
            # Verifica UPDATE
            updated_user = db.execute_query(
                "SELECT * FROM funcionarios WHERE name_id = %s",
                ('test_crud',),
                fetch_one=True
            )
            logger.debug(f"Usuário após UPDATE: {updated_user}")
            
            if not updated_user:
                raise Exception("Usuário não encontrado após UPDATE")
            if updated_user['status'] != 0:
                raise Exception(f"Status não atualizado: {updated_user['status']}")
            
            # DELETE
            logger.debug("Tentando deletar usuário...")
            delete_result = db.execute_query(
                "DELETE FROM funcionarios WHERE name_id = %s",
                ('test_crud',)
            )
            logger.debug(f"Resultado do DELETE: {delete_result}")
            
            # Verifica DELETE
            deleted_check = db.execute_query(
                "SELECT COUNT(*) as count FROM funcionarios WHERE name_id = %s",
                ('test_crud',),
                fetch_one=True
            )
            logger.debug(f"Verificação após DELETE: {deleted_check}")
            
            if deleted_check['count'] > 0:
                raise Exception("Usuário ainda existe após DELETE")
                
            logger.info("Teste CRUD passou")
            
        except Exception as e:
            logger.error(f"Erro no teste CRUD: {e}", exc_info=True)
            # Mostra estado atual da tabela
            try:
                current_state = db.execute_query(
                    "SELECT * FROM funcionarios WHERE name_id LIKE 'test_%'"
                )
                logger.error(f"Estado atual da tabela: {current_state}")
            except:
                pass
            raise
        finally:
            self.cleanup()
        
    def test_cache(self):
        """Testa funcionalidade de cache"""
        try:
            from app.data.cache.query_cache import query_cache
            
            # Teste básico de set/get
            cache_key = "test_key"
            test_data = {"test": "data"}
            query_cache.set_query_result("SELECT * FROM test", (), test_data)
            
            # Verifica se foi armazenado
            result = query_cache.get_query_result("SELECT * FROM test", ())
            assert result == test_data, "Cache não retornou dados corretos"
            
            # Verifica contadores
            stats = query_cache.get_stats()
            assert stats['hits'] >= 1, "Contador de hits não incrementou"
            
            # Teste de invalidação
            query_cache.invalidate_patterns([r"SELECT.*FROM.*test"])
            result = query_cache.get_query_result("SELECT * FROM test", ())
            assert result is None, "Cache não foi invalidado corretamente"
            
            # Teste de limite de tamanho
            for i in range(1100):  # Maior que max_size
                query_cache.set_query_result(f"SELECT {i}", (), {"data": i})
            
            assert len(query_cache.cache) <= query_cache.max_size, "Limite de tamanho do cache não respeitado"
            
            # Teste de expiração
            query_cache.set_query_result(
                "test_expire", 
                (), 
                {"data": "test"},
                timeout=timedelta(seconds=1)
            )
            time.sleep(1.1)
            assert query_cache.get_query_result("test_expire", ()) is None, "Cache não expirou"
            
            logger.info("Teste de cache passou")
            return "✅ test_cache passou"
            
        except Exception as e:
            logger.error(f"Erro em test_cache: {e}", exc_info=True)
            return f"❌ test_cache falhou: {str(e)}"
        
    def test_transaction(self):
        """Testa transações"""
        try:
            # Inicia transação
            db.execute_query("START TRANSACTION")
            
            # Operações na transação com todos os campos obrigatórios
            insert_result = db.execute_query(
                """INSERT INTO funcionarios 
                   (name_id, senha, status, nome, email) 
                   VALUES (%s, %s, %s, %s, %s)""",
                ('test_trans', 'test999', 1, 'Teste Trans', 'test@trans.com')
            )
            
            logger.debug(f"Resultado do INSERT: {insert_result}")
            
            # Verifica se foi inserido
            check_insert = db.execute_query(
                "SELECT * FROM funcionarios WHERE name_id = %s",
                ('test_trans',),
                fetch_one=True
            )
            
            if not check_insert:
                db.execute_query("ROLLBACK")
                raise Exception("Registro não foi inserido")
                
            logger.debug(f"Registro inserido: {check_insert}")
            
            try:
                # Força erro com query inválida
                db.execute_query("INSERT INTO tabela_inexistente (campo) VALUES ('teste')")
            except Exception as e:
                logger.info("Erro esperado capturado, executando rollback")
                # Deve reverter
                db.execute_query("ROLLBACK")
                
                # Verifica se reverteu
                check_rollback = db.execute_query(
                    "SELECT * FROM funcionarios WHERE name_id = %s",
                    ('test_trans',),
                    fetch_one=True
                )
                
                if check_rollback:
                    raise Exception("Rollback falhou - registro ainda existe")
                    
                logger.info("Teste de transação passou - rollback funcionou corretamente")
                return "✅ test_transaction passou"
                
            raise Exception("Erro esperado não ocorreu")
            
        except Exception as e:
            logger.error(f"Erro em test_transaction: {e}")
            # Garante rollback em caso de erro
            try:
                db.execute_query("ROLLBACK")
            except:
                pass
            return f"❌ test_transaction falhou: {str(e)}"

    def test_table_structure(self):
        """Verifica estrutura da tabela funcionarios"""
        try:
            # Verifica se a tabela existe
            tables = db.execute_query("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
            """)
            
            if not any(t['TABLE_NAME'] == 'funcionarios' for t in tables):
                # Cria tabela se não existir
                db.execute_query("""
                    CREATE TABLE IF NOT EXISTS funcionarios (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name_id VARCHAR(50) NOT NULL UNIQUE,
                        senha VARCHAR(128) NOT NULL,
                        status TINYINT NOT NULL DEFAULT 1,
                        nome VARCHAR(100) NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
            # Verifica estrutura
            columns = db.execute_query("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'funcionarios'
            """)
            
            required_columns = {'id', 'name_id', 'senha', 'status', 'nome', 'email', 'created_at', 'updated_at'}
            existing_columns = {col['COLUMN_NAME'] for col in columns}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                logger.error(f"Colunas faltando: {missing}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar estrutura: {e}")
            return False

    def cleanup(self):
        """Limpa dados de teste"""
        try:
            db.execute_query("DELETE FROM funcionarios WHERE name_id LIKE 'test_%'")
            query_cache.clear()
        except Exception as e:
            logger.warning(f"Erro ao limpar dados de teste: {e}")

# Script para executar testes
if __name__ == "__main__":
    tester = DatabaseTester()
    results = tester.run_all_tests()
    
    print("\nResultados dos Testes:")
    for result in results:
        print(result) 
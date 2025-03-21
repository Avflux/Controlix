import unittest
import sqlite3
import tempfile
from pathlib import Path
from app.data.migrations.migration_manager import MigrationManager, MigrationError

class TestMigrationManager(unittest.TestCase):
    def setUp(self):
        """Configura ambiente de teste"""
        # Cria bancos temporários para teste
        self.source_file = tempfile.NamedTemporaryFile(delete=False)
        self.target_file = tempfile.NamedTemporaryFile(delete=False)
        self.source_db = Path(self.source_file.name)
        self.target_db = Path(self.target_file.name)
        
        # Fecha os arquivos temporários (sqlite3 vai reabri-los)
        self.source_file.close()
        self.target_file.close()
        
        # Cria schema de teste no banco fonte
        self.source_conn = sqlite3.connect(self.source_db)
        self.source_cursor = self.source_conn.cursor()
        self._create_test_schema(self.source_conn)
        self._insert_test_data(self.source_conn)
        
        # Cria schema idêntico no banco destino
        self.target_conn = sqlite3.connect(self.target_db)
        self.target_cursor = self.target_conn.cursor()
        self._create_test_schema(self.target_conn)
        
        # Cria instância do manager
        self.manager = MigrationManager(self.source_db, self.target_db)
    
    def _create_test_schema(self, conn):
        """Cria schema de teste"""
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            );
            
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()
    
    def _insert_test_data(self, conn):
        """Insere dados de teste"""
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [
                ("User 1", "user1@test.com"),
                ("User 2", "user2@test.com"),
                ("User 3", "user3@test.com")
            ]
        )
        
        cursor.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [
                ("theme", "dark"),
                ("language", "pt-BR")
            ]
        )
        conn.commit()
    
    def tearDown(self):
        """Limpa recursos após cada teste"""
        try:
            # Fecha todas as conexões
            if hasattr(self, 'source_conn'):
                self.source_conn.close()
            if hasattr(self, 'target_conn'):
                self.target_conn.close()
            
            # Remove arquivos temporários
            if hasattr(self, 'source_db'):
                self.source_db.unlink(missing_ok=True)
            if hasattr(self, 'target_db'):
                self.target_db.unlink(missing_ok=True)
                
        except Exception as e:
            print(f"Erro ao limpar recursos: {e}")
    
    def test_successful_migration(self):
        """Testa migração bem sucedida"""
        # Executa migração
        self.assertTrue(self.manager.migrate())
        
        # Verifica dados migrados
        cursor = self.target_conn.cursor()
        
        # Verifica users
        cursor.execute("SELECT COUNT(*) FROM users")
        self.assertEqual(cursor.fetchone()[0], 3)
        
        # Verifica settings
        cursor.execute("SELECT COUNT(*) FROM settings")
        self.assertEqual(cursor.fetchone()[0], 2)
    
    def test_schema_verification(self):
        """Testa verificação de schema"""
        # Recria banco destino com schema diferente
        self.target_conn.close()
        self.target_db.unlink()
        
        self.target_conn = sqlite3.connect(self.target_db)
        self.target_cursor = self.target_conn.cursor()
        self.target_cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT  -- Coluna diferente
            )
        """)
        self.target_conn.commit()
        
        # Tenta migrar
        with self.assertRaises(MigrationError) as context:
            self.manager.migrate()
        
        self.assertIn("Schema incompatível", str(context.exception))
    
    def test_data_integrity(self):
        """Testa verificação de integridade dos dados"""
        # Executa migração
        self.manager.migrate()
        
        # Corrompe dados no destino
        self.target_cursor.execute("UPDATE users SET name = 'Corrupted' WHERE id = 1")
        self.target_conn.commit()
        
        # Verifica integridade
        with self.assertRaises(MigrationError) as context:
            self.manager.verify_migration()
        
        self.assertIn("Falha na verificação de integridade", str(context.exception))
    
    def test_rollback_on_failure(self):
        """Testa rollback em caso de falha"""
        # Insere dados iniciais no destino
        self.target_cursor.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", 
            ("Initial User", "initial@test.com")
        )
        self.target_conn.commit()
        
        # Força erro durante migração corrompendo uma tabela fonte
        self.source_cursor.execute("DROP TABLE settings")
        self.source_conn.commit()
        
        # Tenta migrar
        with self.assertRaises(MigrationError):
            self.manager.migrate()
        
        # Verifica se dados originais foram mantidos
        self.target_cursor.execute("SELECT * FROM users")
        rows = self.target_cursor.fetchall()
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Initial User")
    
    def test_batch_processing(self):
        """Testa processamento em lotes"""
        # Insere mais registros para teste de lotes
        self.source_cursor.executemany(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [("User " + str(i), f"user{i}@test.com") for i in range(4, 104)]
        )
        self.source_conn.commit()
        
        # Migra com lote pequeno
        self.assertTrue(self.manager.migrate(batch_size=10))
        
        # Verifica total de registros migrados
        self.target_cursor.execute("SELECT COUNT(*) FROM users")
        total = self.target_cursor.fetchone()[0]
        
        self.assertEqual(total, 103)  # 3 originais + 100 novos

if __name__ == '__main__':
    unittest.main() 
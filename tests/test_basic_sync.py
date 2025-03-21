import unittest
import sqlite3
import tempfile
import os
import logging
import json
from datetime import datetime, timezone

class TestBasicSync(unittest.TestCase):
    def setUp(self):
        """Prepara ambiente para testes básicos de sincronização"""
        # Configura logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Cria arquivos temporários para os bancos
        self.mysql_file = tempfile.NamedTemporaryFile(delete=False)
        self.sqlite_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Fecha os arquivos para que possam ser usados pelo SQLite
        self.mysql_file.close()
        self.sqlite_file.close()
        
        # Cria conexões
        self.mysql_conn = sqlite3.connect(self.mysql_file.name)
        self.mysql_conn.row_factory = sqlite3.Row
        
        self.sqlite_conn = sqlite3.connect(self.sqlite_file.name)
        self.sqlite_conn.row_factory = sqlite3.Row
        
        # Cria schemas
        self._create_test_schemas()
    
    def tearDown(self):
        """Limpa ambiente após os testes"""
        try:
            # Fecha as conexões antes de tentar excluir os arquivos
            if hasattr(self, 'mysql_conn') and self.mysql_conn:
                self.mysql_conn.close()
            
            if hasattr(self, 'sqlite_conn') and self.sqlite_conn:
                self.sqlite_conn.close()
            
            # Aguarda um momento para garantir que as conexões foram fechadas
            import time
            time.sleep(0.1)
            
            # Tenta excluir os arquivos
            try:
                if hasattr(self, 'mysql_file') and os.path.exists(self.mysql_file.name):
                    os.unlink(self.mysql_file.name)
            except Exception as e:
                logging.warning(f"Não foi possível excluir o arquivo MySQL: {e}")
            
            try:
                if hasattr(self, 'sqlite_file') and os.path.exists(self.sqlite_file.name):
                    os.unlink(self.sqlite_file.name)
            except Exception as e:
                logging.warning(f"Não foi possível excluir o arquivo SQLite: {e}")
        except Exception as e:
            logging.error(f"Erro durante a limpeza: {e}")
    
    def _create_test_schemas(self):
        """Cria schemas de teste em ambos os bancos"""
        # MySQL
        cursor1 = self.mysql_conn.cursor()
        
        cursor1.execute("""
            CREATE TABLE IF NOT EXISTS equipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # SQLite
        cursor2 = self.sqlite_conn.cursor()
        
        cursor2.execute("""
            CREATE TABLE IF NOT EXISTS equipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.mysql_conn.commit()
        self.sqlite_conn.commit()
    
    def test_manual_sync(self):
        """Testa sincronização manual entre MySQL e SQLite"""
        # Insere dados no MySQL
        cursor1 = self.mysql_conn.cursor()
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor1.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe Dev', 'Time de Desenvolvimento', 1, now))
        mysql_id = cursor1.lastrowid
        self.mysql_conn.commit()
        
        # Insere dados no SQLite
        cursor2 = self.sqlite_conn.cursor()
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor2.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe QA', 'Time de Qualidade', 1, now))
        sqlite_id = cursor2.lastrowid
        self.sqlite_conn.commit()
        
        # Verifica dados iniciais
        cursor1.execute("SELECT COUNT(*) FROM equipes")
        mysql_count_before = cursor1.fetchone()[0]
        self.assertEqual(mysql_count_before, 1, "MySQL deve ter 1 equipe antes da sincronização")
        
        cursor2.execute("SELECT COUNT(*) FROM equipes")
        sqlite_count_before = cursor2.fetchone()[0]
        self.assertEqual(sqlite_count_before, 1, "SQLite deve ter 1 equipe antes da sincronização")
        
        # Sincroniza manualmente (MySQL -> SQLite)
        cursor1.execute("SELECT * FROM equipes WHERE id = ?", (mysql_id,))
        mysql_data = dict(cursor1.fetchone())
        
        # Insere dados do MySQL no SQLite
        cursor2.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, (mysql_data['nome'], mysql_data['descricao'], mysql_data['version'], mysql_data['last_modified']))
        self.sqlite_conn.commit()
        
        # Sincroniza manualmente (SQLite -> MySQL)
        cursor2.execute("SELECT * FROM equipes WHERE id = ?", (sqlite_id,))
        sqlite_data = dict(cursor2.fetchone())
        
        # Insere dados do SQLite no MySQL
        cursor1.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, (sqlite_data['nome'], sqlite_data['descricao'], sqlite_data['version'], sqlite_data['last_modified']))
        self.mysql_conn.commit()
        
        # Verifica dados após sincronização
        cursor1.execute("SELECT COUNT(*) FROM equipes")
        mysql_count_after = cursor1.fetchone()[0]
        self.assertEqual(mysql_count_after, 2, "MySQL deve ter 2 equipes após sincronização")
        
        cursor2.execute("SELECT COUNT(*) FROM equipes")
        sqlite_count_after = cursor2.fetchone()[0]
        self.assertEqual(sqlite_count_after, 2, "SQLite deve ter 2 equipes após sincronização")
        
        # Verifica se os dados específicos foram sincronizados
        cursor1.execute("SELECT nome FROM equipes WHERE nome = ?", ('Equipe QA',))
        self.assertIsNotNone(cursor1.fetchone(), "MySQL deve ter a equipe 'Equipe QA'")
        
        cursor2.execute("SELECT nome FROM equipes WHERE nome = ?", ('Equipe Dev',))
        self.assertIsNotNone(cursor2.fetchone(), "SQLite deve ter a equipe 'Equipe Dev'")

if __name__ == '__main__':
    unittest.main() 
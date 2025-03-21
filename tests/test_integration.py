import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
import logging
import json
from app.data.sync.sync_manager import (
    SyncManager, TableConfig, ConflictResolutionStrategy,
    SyncDirection, SyncError
)

class TestIntegration(unittest.TestCase):
    def setUp(self):
        """Prepara ambiente para testes de integração"""
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
        
        # Configura tabelas para sync
        self.table_configs = [
            TableConfig(
                name="equipes",
                conflict_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
                primary_key="id",
                merge_fields=["nome", "descricao"]
            ),
            TableConfig(
                name="usuarios",
                conflict_strategy=ConflictResolutionStrategy.MANUAL_RESOLUTION,
                primary_key="id",
                merge_fields=["nome", "email", "tipo_usuario"]
            ),
            TableConfig(
                name="logs_sistema",
                conflict_strategy=ConflictResolutionStrategy.APPEND_ONLY,
                primary_key="id",
                merge_fields=["acao", "descricao"]
            )
        ]
        
        # Cria schemas
        self._create_test_schemas()
        
        # Cria tabelas de controle de sincronização
        self._create_sync_tables()
        
        # Cria instância do SyncManager
        self.sync_manager = SyncManager(
            mysql_conn=self.mysql_conn,
            sqlite_conn=self.sqlite_conn,
            table_configs=self.table_configs
        )
    
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
        
        cursor1.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipe_id INTEGER,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                name_id TEXT,
                senha TEXT NOT NULL DEFAULT 'senha123',
                tipo_usuario TEXT CHECK(tipo_usuario IN ('admin', 'comum')) DEFAULT 'comum',
                data_entrada TEXT,
                base_value REAL,
                ociosidade TEXT,
                is_logged_in INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id)
            )
        """)
        
        cursor1.execute("""
            CREATE TABLE IF NOT EXISTS logs_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                acao TEXT NOT NULL,
                descricao TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
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
        
        cursor2.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipe_id INTEGER,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                name_id TEXT,
                senha TEXT NOT NULL DEFAULT 'senha123',
                tipo_usuario TEXT CHECK(tipo_usuario IN ('admin', 'comum')) DEFAULT 'comum',
                data_entrada TEXT,
                base_value REAL,
                ociosidade TEXT,
                is_logged_in INTEGER DEFAULT 0,
                status INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipe_id) REFERENCES equipes(id)
            )
        """)
        
        cursor2.execute("""
            CREATE TABLE IF NOT EXISTS logs_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                acao TEXT NOT NULL,
                descricao TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                version INTEGER NOT NULL DEFAULT 1,
                last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        self.mysql_conn.commit()
        self.sqlite_conn.commit()
    
    def _create_sync_tables(self):
        """Cria tabelas de controle de sincronização"""
        # MySQL
        cursor1 = self.mysql_conn.cursor()
        cursor1.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
                old_data TEXT,  -- JSON
                new_data TEXT,  -- JSON
                version INTEGER NOT NULL,
                sync_status TEXT NOT NULL CHECK (sync_status IN ('PENDING', 'SYNCED', 'CONFLICT', 'ERROR')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor1.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(sync_status)
        """)
        
        cursor1.execute("""
            CREATE INDEX IF NOT EXISTS idx_table_record ON sync_log(table_name, record_id)
        """)
        
        cursor1.execute("""
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                mysql_data TEXT NOT NULL,  -- JSON
                sqlite_data TEXT NOT NULL,  -- JSON
                mysql_version INTEGER NOT NULL,
                sqlite_version INTEGER NOT NULL,
                mysql_modified TEXT,
                sqlite_modified TEXT,
                resolution_strategy TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by TEXT,
                resolution_data TEXT  -- JSON
            )
        """)
        
        # SQLite
        cursor2 = self.sqlite_conn.cursor()
        cursor2.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
                old_data TEXT,  -- JSON
                new_data TEXT,  -- JSON
                version INTEGER NOT NULL,
                sync_status TEXT NOT NULL CHECK (sync_status IN ('PENDING', 'SYNCED', 'CONFLICT', 'ERROR')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor2.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(sync_status)
        """)
        
        cursor2.execute("""
            CREATE INDEX IF NOT EXISTS idx_table_record ON sync_log(table_name, record_id)
        """)
        
        cursor2.execute("""
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                mysql_data TEXT NOT NULL,  -- JSON
                sqlite_data TEXT NOT NULL,  -- JSON
                mysql_version INTEGER NOT NULL,
                sqlite_version INTEGER NOT NULL,
                mysql_modified TEXT,
                sqlite_modified TEXT,
                resolution_strategy TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by TEXT,
                resolution_data TEXT  -- JSON
            )
        """)
        
        self.mysql_conn.commit()
        self.sqlite_conn.commit()
    
    def test_full_sync_cycle(self):
        """Testa ciclo completo de sincronização com todas as tabelas"""
        # Insere dados no MySQL
        cursor1 = self.mysql_conn.cursor()
        
        # Insere equipe
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor1.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe Dev', 'Time de Desenvolvimento', 1, now))
        equipe_id = cursor1.lastrowid
        
        # Insere usuário
        cursor1.execute("""
            INSERT INTO usuarios (equipe_id, nome, email, tipo_usuario, senha, version, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (equipe_id, 'João Dev', 'joao@dev.com', 'admin', 'senha123', 1, now))
        usuario_id = cursor1.lastrowid
        
        # Insere log
        cursor1.execute("""
            INSERT INTO logs_sistema (usuario_id, acao, descricao, version, last_modified)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario_id, 'CRIAR_EQUIPE', 'Criou nova equipe de desenvolvimento', 1, now))
        
        # Registra as alterações no log de sincronização
        cursor1.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('equipes', equipe_id, 'INSERT', json.dumps({'id': equipe_id, 'nome': 'Equipe Dev', 'descricao': 'Time de Desenvolvimento', 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        cursor1.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('usuarios', usuario_id, 'INSERT', json.dumps({'id': usuario_id, 'equipe_id': equipe_id, 'nome': 'João Dev', 'email': 'joao@dev.com', 'tipo_usuario': 'admin', 'senha': 'senha123', 'status': 1, 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.mysql_conn.commit()
        
        # Insere dados diferentes no SQLite
        cursor2 = self.sqlite_conn.cursor()
        
        # Insere outra equipe
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor2.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe QA', 'Time de Qualidade', 1, now))
        equipe_qa_id = cursor2.lastrowid
        
        # Insere outro usuário
        cursor2.execute("""
            INSERT INTO usuarios (equipe_id, nome, email, tipo_usuario, senha, version, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (equipe_qa_id, 'Maria QA', 'maria@qa.com', 'comum', 'senha123', 1, now))
        usuario_qa_id = cursor2.lastrowid
        
        # Insere outro log
        cursor2.execute("""
            INSERT INTO logs_sistema (usuario_id, acao, descricao, version, last_modified)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario_qa_id, 'CRIAR_EQUIPE', 'Criou nova equipe de QA', 1, now))
        
        # Registra as alterações no log de sincronização
        cursor2.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('equipes', equipe_qa_id, 'INSERT', json.dumps({'id': equipe_qa_id, 'nome': 'Equipe QA', 'descricao': 'Time de Qualidade', 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        cursor2.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('usuarios', usuario_qa_id, 'INSERT', json.dumps({'id': usuario_qa_id, 'equipe_id': equipe_qa_id, 'nome': 'Maria QA', 'email': 'maria@qa.com', 'tipo_usuario': 'comum', 'senha': 'senha123', 'status': 1, 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.sqlite_conn.commit()
        
        # Executa sincronização
        result = self.sync_manager.synchronize()
        logging.info(f"Resultado da sincronização: {result}")
        
        # Verifica se os dados foram sincronizados corretamente
        # MySQL
        cursor1.execute("SELECT COUNT(*) FROM equipes")
        mysql_equipes = cursor1.fetchone()[0]
        logging.info(f"MySQL equipes count: {mysql_equipes}")
        self.assertEqual(mysql_equipes, 2, "MySQL deve ter 2 equipes após sincronização")
        
        cursor1.execute("SELECT COUNT(*) FROM usuarios")
        mysql_usuarios = cursor1.fetchone()[0]
        logging.info(f"MySQL usuarios count: {mysql_usuarios}")
        self.assertEqual(mysql_usuarios, 2, "MySQL deve ter 2 usuários após sincronização")
        
        cursor1.execute("SELECT COUNT(*) FROM logs_sistema")
        mysql_logs = cursor1.fetchone()[0]
        logging.info(f"MySQL logs count: {mysql_logs}")
        self.assertEqual(mysql_logs, 2, "MySQL deve ter 2 logs após sincronização")
        
        # SQLite
        cursor2.execute("SELECT COUNT(*) FROM equipes")
        sqlite_equipes = cursor2.fetchone()[0]
        logging.info(f"SQLite equipes count: {sqlite_equipes}")
        self.assertEqual(sqlite_equipes, 2, "SQLite deve ter 2 equipes após sincronização")
        
        cursor2.execute("SELECT COUNT(*) FROM usuarios")
        sqlite_usuarios = cursor2.fetchone()[0]
        logging.info(f"SQLite usuarios count: {sqlite_usuarios}")
        self.assertEqual(sqlite_usuarios, 2, "SQLite deve ter 2 usuários após sincronização")
        
        cursor2.execute("SELECT COUNT(*) FROM logs_sistema")
        sqlite_logs = cursor2.fetchone()[0]
        logging.info(f"SQLite logs count: {sqlite_logs}")
        self.assertEqual(sqlite_logs, 2, "SQLite deve ter 2 logs após sincronização")
    
    def test_fallback_scenario(self):
        """Testa cenário de fallback quando MySQL está indisponível"""
        # Primeiro, insere alguns dados no MySQL
        cursor1 = self.mysql_conn.cursor()
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor1.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe Principal', 'Equipe Principal do Projeto', 1, now))
        equipe_id = cursor1.lastrowid
        
        # Registra a alteração no log de sincronização
        cursor1.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('equipes', equipe_id, 'INSERT', json.dumps({'id': equipe_id, 'nome': 'Equipe Principal', 'descricao': 'Equipe Principal do Projeto', 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.mysql_conn.commit()
        
        # Fecha conexão MySQL para simular indisponibilidade
        self.mysql_conn.close()
        self.mysql_conn = None  # Importante para o tearDown
        
        # Tenta sincronizar - deve usar apenas SQLite
        try:
            self.sync_manager.synchronize(direction=SyncDirection.SQLITE_TO_MYSQL)
            self.fail("Deveria ter lançado exceção")
        except SyncError as e:
            self.assertIn("Falha na sincronização", str(e))
        
        # Verifica se os dados no SQLite continuam acessíveis
        cursor2 = self.sqlite_conn.cursor()
        cursor2.execute("SELECT COUNT(*) FROM equipes")
        count_before = cursor2.fetchone()[0]
        
        # Insere novo registro no SQLite durante fallback
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor2.execute("""
            INSERT INTO equipes (nome, descricao, version, last_modified)
            VALUES (?, ?, ?, ?)
        """, ('Equipe Backup', 'Equipe de Contingência', 1, now))
        equipe_id = cursor2.lastrowid
        
        # Registra a alteração no log de sincronização
        cursor2.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('equipes', equipe_id, 'INSERT', json.dumps({'id': equipe_id, 'nome': 'Equipe Backup', 'descricao': 'Equipe de Contingência', 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.sqlite_conn.commit()
        
        # Verifica se registro foi inserido
        cursor2.execute("SELECT COUNT(*) FROM equipes")
        count_after = cursor2.fetchone()[0]
        self.assertEqual(count_after, count_before + 1)
        
        # Reconecta MySQL
        self.mysql_conn = sqlite3.connect(self.mysql_file.name)
        self.mysql_conn.row_factory = sqlite3.Row
        self.sync_manager._mysql_conn = self.mysql_conn
        
        # Sincroniza novamente
        self.sync_manager.synchronize()
        
        # Verifica se dados foram sincronizados
        cursor1 = self.mysql_conn.cursor()
        cursor1.execute("SELECT COUNT(*) FROM equipes")
        mysql_count = cursor1.fetchone()[0]
        self.assertEqual(mysql_count, count_after)
    
    def test_error_recovery(self):
        """Testa recuperação de erros durante sincronização"""
        # Insere dados que causarão conflito
        cursor1 = self.mysql_conn.cursor()
        cursor2 = self.sqlite_conn.cursor()
        
        # Mesmo email em ambos os bancos
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor1.execute("""
            INSERT INTO usuarios (nome, email, tipo_usuario, senha, version, last_modified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('User 1', 'conflito@email.com', 'admin', 'senha123', 1, now))
        usuario_id1 = cursor1.lastrowid
        
        # Registra a alteração no log de sincronização
        cursor1.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('usuarios', usuario_id1, 'INSERT', json.dumps({'id': usuario_id1, 'nome': 'User 1', 'email': 'conflito@email.com', 'tipo_usuario': 'admin', 'senha': 'senha123', 'status': 1, 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.mysql_conn.commit()
        
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor2.execute("""
            INSERT INTO usuarios (nome, email, tipo_usuario, senha, version, last_modified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('User 2', 'conflito@email.com', 'comum', 'senha123', 1, now))
        usuario_id2 = cursor2.lastrowid
        
        # Registra a alteração no log de sincronização
        cursor2.execute("""
            INSERT INTO sync_log (table_name, record_id, operation, new_data, version, sync_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('usuarios', usuario_id2, 'INSERT', json.dumps({'id': usuario_id2, 'nome': 'User 2', 'email': 'conflito@email.com', 'tipo_usuario': 'comum', 'senha': 'senha123', 'status': 1, 'version': 1, 'last_modified': now}), 1, 'PENDING'))
        
        self.sqlite_conn.commit()
        
        # Tenta sincronizar - deve detectar conflito
        try:
            self.sync_manager.synchronize()
        except Exception as e:
            logging.error(f"Erro durante sincronização: {e}")
        
        # Verifica se conflito foi registrado
        conflicts = self.sync_manager.get_pending_conflicts()
        self.assertTrue(len(conflicts) > 0, "Deve haver pelo menos um conflito")
        
        if len(conflicts) > 0:
            # Resolve conflito manualmente
            conflict = conflicts[0]
            resolved_data = {
                'id': conflict.record_id,
                'nome': 'User Resolvido',
                'email': 'resolvido@email.com',
                'tipo_usuario': 'admin',
                'senha': 'senha123',
                'status': 1,
                'version': max(conflict.mysql_version or 1, conflict.sqlite_version or 1) + 1,
                'last_modified': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.sync_manager.resolve_conflict_manually(conflict.record_id, resolved_data, 'test_user')
            
            # Verifica se resolução foi aplicada
            cursor1.execute("SELECT email FROM usuarios WHERE id = ?", (conflict.record_id,))
            mysql_result = cursor1.fetchone()
            mysql_email = mysql_result[0] if mysql_result else None
            
            cursor2.execute("SELECT email FROM usuarios WHERE id = ?", (conflict.record_id,))
            sqlite_result = cursor2.fetchone()
            sqlite_email = sqlite_result[0] if sqlite_result else None
            
            if mysql_email and sqlite_email:
                self.assertEqual(mysql_email, 'resolvido@email.com')
                self.assertEqual(sqlite_email, 'resolvido@email.com')
            
            # Verifica se não há mais conflitos pendentes
            conflicts = self.sync_manager.get_pending_conflicts()
            self.assertEqual(len(conflicts), 0)

if __name__ == '__main__':
    unittest.main() 
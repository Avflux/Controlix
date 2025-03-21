#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste simples para verificar a sincronização funciona corretamente com o tipo timedelta.
"""

import os
import sys
import logging
import sqlite3
import mysql.connector
import tempfile
from datetime import timedelta, datetime
import traceback

# Adiciona o diretório raiz ao path para importar módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.settings import DATABASE
from app.data.sync.sync_manager import SyncManager, SyncDirection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'test_timedelta_simple.log'), 'w')
    ]
)

def get_mysql_config():
    """Obtém a configuração do MySQL."""
    return {
        'host': 'localhost',
        'user': 'root',
        'password': 'Gaadvd@1',
        'database': 'chronos_db',
        'port': 3306
    }

def create_test_sqlite_db():
    """Cria um banco de dados SQLite temporário para teste."""
    # Cria um arquivo temporário
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    # Conecta ao banco de dados
    conn = sqlite3.connect(temp_db.name)
    cursor = conn.cursor()
    
    # Cria tabelas necessárias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            equipe_id INTEGER,
            nome TEXT,
            email TEXT,
            senha TEXT,
            tipo_usuario TEXT,
            data_entrada TEXT,
            data_saida TEXT,
            ociosidade REAL,
            status INTEGER,
            updated_at TEXT,
            is_logged_in INTEGER,
            version INTEGER,
            last_modified TEXT
        )
    ''')
    
    # Cria tabelas de sincronização
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id INTEGER,
            operation TEXT,
            timestamp TEXT,
            source TEXT,
            old_data TEXT,
            new_data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id INTEGER,
            mysql_data TEXT,
            sqlite_data TEXT,
            mysql_version INTEGER,
            sqlite_version INTEGER,
            mysql_modified TEXT,
            sqlite_modified TEXT,
            status TEXT,
            resolved_by TEXT,
            resolved_data TEXT,
            created_at TEXT,
            resolved_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Fecha a conexão
    conn.commit()
    conn.close()
    
    logging.info(f"Banco de dados SQLite temporário criado em: {temp_db.name}")
    return temp_db.name

def test_timedelta_sync():
    """Testa a sincronização com tipo timedelta."""
    logging.info("Iniciando teste de sincronização com tipo timedelta")
    
    # Criar banco de dados SQLite temporário
    temp_db_path = create_test_sqlite_db()
    
    # Conectar ao MySQL
    logging.info("Conectando ao MySQL...")
    mysql_config = get_mysql_config()
    mysql_conn = mysql.connector.connect(**mysql_config)
    logging.info("Conexão MySQL estabelecida")
    
    # Conectar ao SQLite temporário
    logging.info(f"Conectando ao SQLite temporário: {temp_db_path}...")
    sqlite_conn = sqlite3.connect(temp_db_path)
    logging.info("Conexão SQLite estabelecida")
    
    try:
        # Verificar se a tabela 'usuarios' existe no MySQL
        mysql_cursor = mysql_conn.cursor(dictionary=True)
        mysql_cursor.execute("SHOW TABLES LIKE 'usuarios'")
        if mysql_cursor.fetchone():
            logging.info("Tabela 'usuarios' encontrada no MySQL")
        else:
            logging.error("Tabela 'usuarios' não encontrada no MySQL")
            return
        
        # Verificar se a coluna 'ociosidade' existe na tabela 'usuarios' do MySQL
        mysql_cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'ociosidade'")
        ociosidade_column = mysql_cursor.fetchone()
        if ociosidade_column:
            logging.info(f"Coluna 'ociosidade' encontrada no MySQL com tipo: {ociosidade_column['Type']}")
        else:
            logging.error("Coluna 'ociosidade' não encontrada na tabela 'usuarios' do MySQL")
            return
        
        # Criar um valor de timedelta para teste
        test_timedelta = timedelta(hours=2, minutes=30, seconds=15)
        logging.info(f"Usando timedelta de teste: {test_timedelta} ({test_timedelta.total_seconds()} segundos)")
        
        # Verificar se o registro de teste já existe
        mysql_cursor.execute("SELECT * FROM usuarios WHERE id = 9999")
        existing_record = mysql_cursor.fetchone()
        if existing_record:
            logging.info(f"Registro de teste (ID=9999) já existe no MySQL")
            # Atualizar o registro existente com o novo valor de timedelta
            mysql_cursor.execute(
                "UPDATE usuarios SET nome = 'Teste Timedelta', email = 'teste@timedelta.com', "
                "ociosidade = %s, updated_at = NOW(), version = version + 1, last_modified = NOW() "
                "WHERE id = 9999",
                (test_timedelta,)
            )
            logging.info(f"Registro atualizado com timedelta: {test_timedelta}")
        else:
            # Inserir um novo registro com timedelta
            mysql_cursor.execute(
                "INSERT INTO usuarios (id, nome, email, senha, tipo_usuario, data_entrada, ociosidade, "
                "status, updated_at, is_logged_in, version, last_modified) "
                "VALUES (9999, 'Teste Timedelta', 'teste@timedelta.com', 'senha123', 'comum', "
                "CURDATE(), %s, 1, NOW(), 0, 1, NOW())",
                (test_timedelta,)
            )
            logging.info(f"Novo registro inserido com timedelta: {test_timedelta}")
        
        mysql_conn.commit()
        logging.info("Registro salvo com sucesso no MySQL")
        
        # Verificar o registro inserido/atualizado
        mysql_cursor.execute("SELECT * FROM usuarios WHERE id = 9999")
        test_record = mysql_cursor.fetchone()
        if test_record:
            logging.info(f"Registro de teste encontrado no MySQL: {test_record}")
        else:
            logging.error("Registro de teste não encontrado no MySQL após inserção/atualização")
            return
        
        # Criar a tabela usuarios no SQLite para o teste
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                equipe_id INTEGER,
                nome TEXT,
                email TEXT,
                name_id TEXT,
                senha TEXT,
                tipo_usuario TEXT,
                data_entrada TEXT,
                base_value REAL,
                data_saida TEXT,
                ociosidade REAL,
                status INTEGER,
                updated_at TEXT,
                is_logged_in INTEGER,
                version INTEGER DEFAULT 1,
                last_modified TEXT
            )
        """)
        sqlite_conn.commit()
        logging.info("Tabela 'usuarios' criada no SQLite")
        
        # Criar instância do SyncManager
        logging.info(f"Criando instância do SyncManager com banco SQLite temporário...")
        sync_manager = SyncManager(
            mysql_config=mysql_config,
            sqlite_path=temp_db_path
        )
        logging.info("SyncManager criado com sucesso")
        
        # Sincronizar do MySQL para o SQLite
        logging.info("Iniciando sincronização MySQL -> SQLite")
        sync_stats = sync_manager.synchronize(SyncDirection.MYSQL_TO_SQLITE)
        
        # Registrar estatísticas de sincronização
        logging.info(f"Sincronização concluída em {sync_stats.get('duration', 0):.2f} segundos")
        logging.info(f"Registros sincronizados: {sync_stats.get('records_synced', 0)}")
        logging.info(f"Conflitos: {sync_stats.get('conflicts', 0)}")
        logging.info(f"Estatísticas completas: {sync_stats}")
        
        if sync_stats.get('errors', 0) > 0:
            logging.error("Erros encontrados durante a sincronização")
            return
        
        # Verificar se o registro foi sincronizado para o SQLite
        logging.info(f"Verificando se o registro (ID=9999) foi sincronizado para o SQLite...")
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM usuarios WHERE id = 9999")
        sqlite_record = sqlite_cursor.fetchone()
        
        if sqlite_record:
            logging.info(f"Registro encontrado no SQLite: {sqlite_record}")
            # Verificar se o valor de timedelta foi convertido corretamente
            ociosidade_index = [i for i, desc in enumerate(sqlite_cursor.description) if desc[0] == 'ociosidade'][0]
            ociosidade_value = sqlite_record[ociosidade_index]
            logging.info(f"Valor de ociosidade no SQLite: {ociosidade_value}")
            
            # Verificar se o valor está próximo do esperado (9015 segundos)
            expected_seconds = test_timedelta.total_seconds()
            if isinstance(ociosidade_value, (int, float)) and abs(ociosidade_value - expected_seconds) < 1:
                logging.info(f"SUCESSO: Valor de timedelta convertido corretamente: {ociosidade_value} segundos")
            else:
                logging.error(f"FALHA: Valor de timedelta não foi convertido corretamente. Esperado: {expected_seconds}, Obtido: {ociosidade_value}")
        else:
            logging.error("FALHA: Registro não encontrado no SQLite após sincronização (ID=9999)")
        
    finally:
        # Fechar conexões
        if 'mysql_cursor' in locals():
            mysql_cursor.close()
        if 'mysql_conn' in locals() and mysql_conn.is_connected():
            mysql_conn.close()
            logging.info("Conexão MySQL fechada")
        
        if 'sqlite_cursor' in locals():
            sqlite_cursor.close()
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
            logging.info("Conexão SQLite fechada")
        
        # Remover arquivo temporário
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
            logging.info(f"Arquivo temporário removido: {temp_db_path}")

def main():
    """Função principal"""
    logging.info("=== Iniciando teste simples de sincronização com timedelta ===")
    
    try:
        test_timedelta_sync()
        logging.info("=== Teste de sincronização com timedelta concluído ===")
        return 0
    except Exception as e:
        logging.error(f"Erro não tratado: {e}")
        logging.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
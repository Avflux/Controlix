#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Teste de sincronização entre MySQL e SQLite com diferenças de schema.

Este script testa se a sincronização funciona corretamente quando há diferenças
de schema entre os bancos de dados MySQL e SQLite, como a presença da coluna
'data_saida' no MySQL mas não no SQLite, e a conversão de tipos de dados
incompatíveis como datetime.timedelta.
"""

import os
import sys
import logging
import sqlite3
import mysql.connector
from datetime import datetime, timedelta
import time
import random
import string

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.sync.sync_manager import SyncManager, TableConfig, ConflictResolutionStrategy, SyncDirection
from app.data.connection import DatabaseConnection

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_column_sync.log', mode='w'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('test_column_sync')

def random_string(length=10):
    """Gera uma string aleatória para testes"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def check_mysql_connection():
    """Verifica a conexão com o MySQL"""
    try:
        # Usa o DatabaseConnection para obter a conexão
        db_connection = DatabaseConnection()
        mysql_connected = db_connection.is_mysql_available
        
        if mysql_connected:
            logger.info("Conexão com MySQL estabelecida com sucesso")
            return True
        else:
            logger.warning("MySQL não está disponível")
            return False
    except Exception as e:
        logger.error(f"Erro ao conectar ao MySQL: {e}", exc_info=True)
        return False

def test_column_sync():
    """Testa a sincronização com diferenças de schema"""
    try:
        # Obtém conexões usando o DatabaseConnection
        db_connection = DatabaseConnection()
        
        if not db_connection.is_mysql_available:
            logger.error("MySQL não está disponível. Teste abortado.")
            return False
        
        # Obtém conexões diretas para manipulação de schema
        mysql_conn = db_connection.get_mysql_connection()
        sqlite_conn = db_connection.get_sqlite_connection()
        
        mysql_cursor = mysql_conn.cursor()
        
        # Verifica se a coluna data_saida existe na tabela usuarios do MySQL
        mysql_cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'usuarios'
            AND COLUMN_NAME = 'data_saida'
        """)
        
        if mysql_cursor.fetchone()[0] == 0:
            logger.info("Adicionando coluna 'data_saida' à tabela 'usuarios' no MySQL")
            mysql_cursor.execute("""
                ALTER TABLE usuarios
                ADD COLUMN data_saida DATETIME NULL
            """)
            mysql_conn.commit()
        else:
            logger.info("Coluna 'data_saida' já existe na tabela 'usuarios' do MySQL")
        
        # Verifica se a coluna ociosidade existe na tabela usuarios do MySQL
        mysql_cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'usuarios'
            AND COLUMN_NAME = 'ociosidade'
        """)
        
        if mysql_cursor.fetchone()[0] == 0:
            logger.info("Adicionando coluna 'ociosidade' à tabela 'usuarios' no MySQL")
            mysql_cursor.execute("""
                ALTER TABLE usuarios
                ADD COLUMN ociosidade TIME NULL
            """)
            mysql_conn.commit()
        else:
            logger.info("Coluna 'ociosidade' já existe na tabela 'usuarios' do MySQL")
        
        sqlite_cursor = sqlite_conn.cursor()
        
        # Verifica se a coluna data_saida existe na tabela usuarios do SQLite
        sqlite_cursor.execute("""
            PRAGMA table_info(usuarios)
        """)
        
        columns = [row[1] for row in sqlite_cursor.fetchall()]
        if 'data_saida' in columns:
            logger.info("Coluna 'data_saida' já existe na tabela 'usuarios' do SQLite")
        else:
            logger.info("Coluna 'data_saida' não existe na tabela 'usuarios' do SQLite")
        
        # Limpa dados de teste anteriores
        test_email = f"test_{random_string()}@example.com"
        mysql_cursor.execute("DELETE FROM usuarios WHERE email = %s", (test_email,))
        mysql_conn.commit()
        
        # Insere um registro de teste no MySQL com um campo timedelta
        current_time = datetime.now()
        ociosidade = timedelta(hours=2, minutes=30)  # 2 horas e 30 minutos
        
        mysql_cursor.execute("""
            INSERT INTO usuarios (
                equipe_id, nome, email, senha, tipo_usuario, 
                status, updated_at, data_saida, ociosidade
            ) VALUES (
                1, %s, %s, %s, 'comum', 
                1, %s, %s, %s
            )
        """, (
            f"Teste {random_string()}", 
            test_email,
            "senha123",
            current_time,
            current_time + timedelta(days=30),  # data_saida em 30 dias
            ociosidade
        ))
        mysql_conn.commit()
        
        # Obtém o ID do registro inserido
        mysql_cursor.execute("SELECT id FROM usuarios WHERE email = %s", (test_email,))
        user_id = mysql_cursor.fetchone()[0]
        logger.info(f"Registro de teste inserido no MySQL com ID {user_id}")
        
        # Cria o gerenciador de sincronização
        table_configs = [
            TableConfig(
                name="usuarios",
                primary_key='id',
                merge_fields=['email'],
                conflict_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS
            )
        ]
        
        # Cria o SyncManager com as conexões existentes
        sync_manager = SyncManager(
            table_configs=table_configs,
            mysql_conn=mysql_conn,
            sqlite_conn=sqlite_conn
        )
        
        # Executa a sincronização do MySQL para o SQLite
        start_time = time.time()
        result = sync_manager.synchronize(
            direction=SyncDirection.MYSQL_TO_SQLITE
        )
        end_time = time.time()
        
        logger.info(f"Sincronização concluída em {end_time - start_time:.2f} segundos")
        logger.info(f"Registros sincronizados: {result.get('records_synced', 0)}")
        logger.info(f"Conflitos encontrados: {result.get('conflicts', 0)}")
        
        # Verifica se o registro foi sincronizado para o SQLite
        sqlite_cursor.execute("SELECT id, email, ociosidade FROM usuarios WHERE email = ?", (test_email,))
        sqlite_record = sqlite_cursor.fetchone()
        
        if sqlite_record:
            logger.info(f"Registro encontrado no SQLite: ID={sqlite_record[0]}, Email={sqlite_record[1]}, Ociosidade={sqlite_record[2]}")
            
            # Verifica se o campo ociosidade foi convertido corretamente
            ociosidade_seconds = ociosidade.total_seconds()
            sqlite_ociosidade = sqlite_record[2]
            
            if sqlite_ociosidade is not None:
                logger.info(f"Valor de ociosidade no MySQL: {ociosidade_seconds} segundos")
                logger.info(f"Valor de ociosidade no SQLite: {sqlite_ociosidade}")
                
                # Verifica se os valores são aproximadamente iguais (pode haver pequenas diferenças de precisão)
                if abs(float(sqlite_ociosidade) - ociosidade_seconds) < 0.1:
                    logger.info("Teste PASSOU: O campo timedelta foi convertido corretamente")
                else:
                    logger.error(f"Teste FALHOU: O campo timedelta não foi convertido corretamente. Esperado: {ociosidade_seconds}, Obtido: {sqlite_ociosidade}")
                    return False
            else:
                logger.error("Teste FALHOU: O campo ociosidade é None no SQLite")
                return False
            
            return True
        else:
            logger.error(f"Teste FALHOU: Registro não encontrado no SQLite após sincronização")
            return False
    
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}", exc_info=True)
        return False
    finally:
        # Não fechamos as conexões aqui, pois elas são gerenciadas pelo DatabaseConnection
        pass

def main():
    """Função principal"""
    logger.info("Iniciando teste de sincronização com diferenças de schema")
    
    if not check_mysql_connection():
        logger.error("Não foi possível conectar ao MySQL. Teste abortado.")
        sys.exit(1)
    
    success = test_column_sync()
    
    if success:
        logger.info("Teste de sincronização concluído com SUCESSO")
        sys.exit(0)
    else:
        logger.error("Teste de sincronização FALHOU")
        sys.exit(1)

if __name__ == "__main__":
    main() 
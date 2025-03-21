#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a sincronização entre MySQL local e remoto.
Executa operações básicas e verifica se a sincronização funciona corretamente.
"""

import os
import sys
import logging
import time
import json
from datetime import datetime
import argparse

# Adicionar diretório raiz ao path para importações relativas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.data.mysql.mysql_connection import MySQLConnection
from app.data.mysql.sync_manager import MySQLSyncManager, SyncDirection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test_sync')

def setup_test_data(db_connection, is_local=True):
    """
    Configura dados de teste no banco de dados.
    
    Args:
        db_connection: Conexão com o banco de dados
        is_local: Se True, usa o banco local, caso contrário o remoto
    """
    logger.info(f"Configurando dados de teste no banco {'local' if is_local else 'remoto'}")
    
    try:
        # Limpar dados existentes
        tables = ['atividades', 'user_lock_unlock', 'logs_sistema', 'usuarios', 'funcionarios', 'equipes']
        for table in tables:
            try:
                db_connection.execute_update(f"DELETE FROM {table}", is_local=is_local)
                logger.info(f"Tabela {table} limpa")
            except Exception as e:
                logger.warning(f"Erro ao limpar tabela {table}: {e}")
        
        # Inserir dados de teste na tabela equipes
        equipes_data = [
            ("Equipe de Teste 1", "Descrição da equipe 1"),
            ("Equipe de Teste 2", "Descrição da equipe 2"),
            ("Equipe de Teste 3", "Descrição da equipe 3")
        ]
        
        for equipe in equipes_data:
            try:
                # Verificar se a equipe já existe
                query = "SELECT id FROM equipes WHERE nome = %s"
                result = db_connection.execute_query(query, (equipe[0],), is_local=is_local)
                
                if not result:
                    # Inserir apenas se não existir
                    query = "INSERT INTO equipes (nome, descricao) VALUES (%s, %s)"
                    db_connection.execute_update(query, equipe, is_local=is_local)
                    logger.info(f"Equipe '{equipe[0]}' inserida")
                else:
                    logger.info(f"Equipe '{equipe[0]}' já existe, pulando")
            except Exception as e:
                logger.warning(f"Erro ao inserir equipe '{equipe[0]}': {e}")
        
        logger.info(f"Dados de teste inseridos no banco {'local' if is_local else 'remoto'}")
    except Exception as e:
        logger.error(f"Erro ao configurar dados de teste: {e}")
        raise

def test_sync_local_to_remote(sync_manager):
    """
    Testa a sincronização do banco local para o remoto.
    
    Args:
        sync_manager: Gerenciador de sincronização
    """
    logger.info("Testando sincronização do banco local para o remoto")
    
    try:
        # Inserir dados no banco local
        db_connection = MySQLConnection()
        
        # Obter IDs das equipes
        equipes = db_connection.execute_query("SELECT id, nome FROM equipes", is_local=True)
        equipe_id = equipes[0]['id'] if equipes else 1
        
        # Inserir usuário no banco local
        usuario_data = (
            equipe_id,
            f"Usuário Local {datetime.now().strftime('%H:%M:%S')}",
            f"usuario_local_{int(time.time())}@example.com",
            f"user_{int(time.time())}",
            "senha123",
            "comum"
        )
        
        query = """
            INSERT INTO usuarios (equipe_id, nome, email, name_id, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        db_connection.execute_update(query, usuario_data, is_local=True)
        logger.info("Usuário inserido no banco local")
        
        # Sincronizar do local para o remoto
        stats = sync_manager.synchronize(SyncDirection.LOCAL_TO_REMOTE)
        logger.info(f"Sincronização concluída: {json.dumps(stats, default=str)}")
        
        # Verificar se o usuário foi sincronizado para o remoto
        email = usuario_data[2]
        remote_user = db_connection.execute_query(
            "SELECT * FROM usuarios WHERE email = %s",
            (email,),
            is_local=False
        )
        
        if remote_user:
            logger.info(f"Usuário encontrado no banco remoto: {remote_user[0]['nome']}")
            return True
        else:
            logger.error(f"Usuário não encontrado no banco remoto após sincronização")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar sincronização local para remoto: {e}")
        return False

def test_sync_remote_to_local(sync_manager):
    """
    Testa a sincronização do banco remoto para o local.
    
    Args:
        sync_manager: Gerenciador de sincronização
    """
    logger.info("Testando sincronização do banco remoto para o local")
    
    try:
        # Inserir dados no banco remoto
        db_connection = MySQLConnection()
        
        # Obter IDs das equipes
        equipes = db_connection.execute_query("SELECT id, nome FROM equipes", is_local=False)
        equipe_id = equipes[0]['id'] if equipes else 1
        
        # Inserir usuário no banco remoto
        usuario_data = (
            equipe_id,
            f"Usuário Remoto {datetime.now().strftime('%H:%M:%S')}",
            f"usuario_remoto_{int(time.time())}@example.com",
            f"user_remote_{int(time.time())}",
            "senha456",
            "comum"
        )
        
        query = """
            INSERT INTO usuarios (equipe_id, nome, email, name_id, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        db_connection.execute_update(query, usuario_data, is_local=False)
        logger.info("Usuário inserido no banco remoto")
        
        # Sincronizar do remoto para o local
        stats = sync_manager.synchronize(SyncDirection.REMOTE_TO_LOCAL)
        logger.info(f"Sincronização concluída: {json.dumps(stats, default=str)}")
        
        # Verificar se o usuário foi sincronizado para o local
        email = usuario_data[2]
        local_user = db_connection.execute_query(
            "SELECT * FROM usuarios WHERE email = %s",
            (email,),
            is_local=True
        )
        
        if local_user:
            logger.info(f"Usuário encontrado no banco local: {local_user[0]['nome']}")
            return True
        else:
            logger.error(f"Usuário não encontrado no banco local após sincronização")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar sincronização remoto para local: {e}")
        return False

def test_conflict_resolution(sync_manager):
    """
    Testa a resolução de conflitos durante a sincronização.
    
    Args:
        sync_manager: Gerenciador de sincronização
    """
    logger.info("Testando resolução de conflitos")
    
    try:
        # Inserir dados no banco local e remoto
        db_connection = MySQLConnection()
        
        # Obter IDs das equipes
        equipes_local = db_connection.execute_query("SELECT id, nome FROM equipes", is_local=True)
        equipes_remote = db_connection.execute_query("SELECT id, nome FROM equipes", is_local=False)
        
        equipe_id_local = equipes_local[0]['id'] if equipes_local else 1
        equipe_id_remote = equipes_remote[0]['id'] if equipes_remote else 1
        
        # Criar usuário com nomes diferentes em cada banco, mas mesmo ID
        # Primeiro, inserir no banco local
        local_name = f"Usuário Local Conflito {datetime.now().strftime('%H:%M:%S')}"
        timestamp = int(time.time())
        email = f"conflito_{timestamp}@example.com"
        name_id = f"user_conflict_{timestamp}"
        
        # Inserir no banco local
        query = """
            INSERT INTO usuarios (equipe_id, nome, email, name_id, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        local_data = (
            equipe_id_local,
            local_name,
            email,
            name_id,
            "senha_local",
            "comum"
        )
        
        db_connection.execute_update(query, local_data, is_local=True)
        logger.info(f"Usuário '{local_name}' inserido no banco local")
        
        # Obter ID do usuário inserido
        user_query = "SELECT id FROM usuarios WHERE email = %s"
        user_result = db_connection.execute_query(user_query, (email,), is_local=True)
        
        if not user_result:
            logger.error("Não foi possível obter o ID do usuário inserido no banco local")
            return False
        
        user_id = user_result[0]['id']
        logger.info(f"ID do usuário inserido no banco local: {user_id}")
        
        # Atualizar o usuário no banco remoto com um nome diferente
        remote_name = f"Usuário Remoto Conflito {datetime.now().strftime('%H:%M:%S')}"
        
        # Primeiro, verificar se o usuário já existe no banco remoto
        remote_user = db_connection.execute_query(user_query, (email,), is_local=False)
        
        if remote_user:
            # Atualizar o usuário existente
            update_query = "UPDATE usuarios SET nome = %s, version = version + 1 WHERE email = %s"
            db_connection.execute_update(update_query, (remote_name, email), is_local=False)
            logger.info(f"Usuário '{remote_name}' atualizado no banco remoto")
        else:
            # Inserir o usuário no banco remoto
            remote_data = (
                equipe_id_remote,
                remote_name,
                email,
                name_id,
                "senha_remota",
                "comum"
            )
            db_connection.execute_update(query, remote_data, is_local=False)
            logger.info(f"Usuário '{remote_name}' inserido no banco remoto")
        
        # Sincronizar bidirecional
        stats = sync_manager.synchronize(SyncDirection.BIDIRECTIONAL)
        logger.info(f"Sincronização concluída: {json.dumps(stats, default=str)}")
        
        # Verificar se o conflito foi resolvido (remoto deve prevalecer)
        local_user = db_connection.execute_query(
            "SELECT * FROM usuarios WHERE email = %s",
            (email,),
            is_local=True
        )
        
        remote_user = db_connection.execute_query(
            "SELECT * FROM usuarios WHERE email = %s",
            (email,),
            is_local=False
        )
        
        if local_user and remote_user:
            logger.info(f"Usuário local após resolução: {local_user[0]['nome']}")
            logger.info(f"Usuário remoto após resolução: {remote_user[0]['nome']}")
            
            # Verificar se o usuário local foi atualizado com os dados do remoto
            if local_user[0]['nome'] == remote_user[0]['nome']:
                logger.info("Conflito resolvido corretamente (remoto prevaleceu)")
                return True
            else:
                logger.error("Conflito não foi resolvido corretamente")
                return False
        else:
            logger.error("Usuário não encontrado após sincronização")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar resolução de conflitos: {e}")
        return False

def main():
    """Função principal para executar os testes de sincronização."""
    parser = argparse.ArgumentParser(description='Testa a sincronização entre MySQL local e remoto')
    parser.add_argument('--setup', action='store_true', help='Configurar dados de teste')
    parser.add_argument('--local-to-remote', action='store_true', help='Testar sincronização local para remoto')
    parser.add_argument('--remote-to-local', action='store_true', help='Testar sincronização remoto para local')
    parser.add_argument('--conflict', action='store_true', help='Testar resolução de conflitos')
    parser.add_argument('--all', action='store_true', help='Executar todos os testes')
    
    args = parser.parse_args()
    
    # Se nenhum argumento for fornecido, mostrar ajuda
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    try:
        # Inicializar conexão e gerenciador de sincronização
        db_connection = MySQLConnection()
        sync_manager = MySQLSyncManager()
        
        # Configurar dados de teste
        if args.setup or args.all:
            setup_test_data(db_connection, is_local=True)
            setup_test_data(db_connection, is_local=False)
        
        # Executar testes
        results = {}
        
        if args.local_to_remote or args.all:
            results['local_to_remote'] = test_sync_local_to_remote(sync_manager)
        
        if args.remote_to_local or args.all:
            results['remote_to_local'] = test_sync_remote_to_local(sync_manager)
        
        if args.conflict or args.all:
            results['conflict'] = test_conflict_resolution(sync_manager)
        
        # Exibir resultados
        logger.info("Resultados dos testes:")
        for test, result in results.items():
            logger.info(f"  {test}: {'SUCESSO' if result else 'FALHA'}")
        
        # Verificar se todos os testes foram bem-sucedidos
        if all(results.values()):
            logger.info("Todos os testes foram bem-sucedidos!")
            return 0
        else:
            logger.error("Alguns testes falharam!")
            return 1
    except Exception as e:
        logger.error(f"Erro ao executar testes: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
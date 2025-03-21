#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar as credenciais do MySQL a partir do arquivo criptografado
e executar os testes de sincronização.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Adicionar diretório raiz ao path para importações relativas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.config.encrypted_settings import encrypted_settings
from app.data.mysql.test_sync import main as run_tests

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('run_tests')

def setup_mysql_credentials():
    """
    Configura as credenciais do MySQL a partir do arquivo criptografado.
    Define as variáveis de ambiente necessárias para a conexão.
    """
    logger.info("Configurando credenciais do MySQL")
    
    try:
        # Obter credenciais do arquivo criptografado
        db_host = encrypted_settings.get('DB_HOST') or encrypted_settings.get('MYSQL_HOST')
        db_user = encrypted_settings.get('DB_USER') or encrypted_settings.get('MYSQL_USER')
        db_password = encrypted_settings.get('DB_PASSWORD') or encrypted_settings.get('MYSQL_PASSWORD')
        db_name = encrypted_settings.get('DB_NAME') or encrypted_settings.get('MYSQL_DATABASE')
        db_port = encrypted_settings.get('DB_PORT') or encrypted_settings.get('MYSQL_PORT', '3306')
        
        if not db_host or not db_user or not db_password or not db_name:
            logger.error("Credenciais incompletas no arquivo criptografado")
            return False
        
        # Configurar variáveis de ambiente para MySQL local
        os.environ['MYSQL_LOCAL_HOST'] = 'localhost'
        os.environ['MYSQL_LOCAL_PORT'] = db_port
        os.environ['MYSQL_LOCAL_USER'] = db_user
        os.environ['MYSQL_LOCAL_PASSWORD'] = db_password
        os.environ['MYSQL_LOCAL_DATABASE'] = db_name
        
        # Configurar variáveis de ambiente para MySQL remoto
        os.environ['MYSQL_REMOTE_HOST'] = db_host
        os.environ['MYSQL_REMOTE_PORT'] = db_port
        os.environ['MYSQL_REMOTE_USER'] = db_user
        os.environ['MYSQL_REMOTE_PASSWORD'] = db_password
        os.environ['MYSQL_REMOTE_DATABASE'] = db_name
        
        logger.info(f"Credenciais configuradas: Local=localhost, Remoto={db_host}")
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar credenciais: {e}")
        return False

def main():
    """Função principal para configurar credenciais e executar testes."""
    parser = argparse.ArgumentParser(description='Configura credenciais e executa testes de sincronização')
    parser.add_argument('--setup', action='store_true', help='Configurar dados de teste')
    parser.add_argument('--local-to-remote', action='store_true', help='Testar sincronização local para remoto')
    parser.add_argument('--remote-to-local', action='store_true', help='Testar sincronização remoto para local')
    parser.add_argument('--conflict', action='store_true', help='Testar resolução de conflitos')
    parser.add_argument('--all', action='store_true', help='Executar todos os testes')
    
    args = parser.parse_args()
    
    # Se nenhum argumento for fornecido, mostrar ajuda
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    # Configurar credenciais
    if not setup_mysql_credentials():
        logger.error("Falha ao configurar credenciais. Abortando testes.")
        return 1
    
    # Executar testes
    logger.info("Iniciando testes de sincronização")
    
    # Passar argumentos para o script de teste
    sys.argv = [sys.argv[0]]
    if args.setup:
        sys.argv.append('--setup')
    if args.local_to_remote:
        sys.argv.append('--local-to-remote')
    if args.remote_to_local:
        sys.argv.append('--remote-to-local')
    if args.conflict:
        sys.argv.append('--conflict')
    if args.all:
        sys.argv.append('--all')
    
    return run_tests()

if __name__ == "__main__":
    sys.exit(main()) 
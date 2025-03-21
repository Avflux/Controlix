#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface gráfica para testar conexão com bancos MySQL local e remoto.
Permite testar conexões e pesquisar tabelas em ambos os bancos.
"""

import os
import sys
import logging
import mysql.connector
from pathlib import Path
import threading
import time
import customtkinter as ctk
from tkinter import messagebox, scrolledtext, StringVar, ttk
import traceback
import json

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.settings import DATABASE
from app.config.encrypted_settings import encrypted_settings
from app.data.mysql.mysql_connection import MySQLConnection

# Configuração de logging
log_file = 'logs/mysql_connection_tester.log'
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)

logger = logging.getLogger('mysql_connection_tester')
logger.info("="*50)
logger.info("INICIANDO APLICAÇÃO DE TESTE DE CONEXÃO MYSQL")
logger.info("="*50)

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

class RedirectText:
    """Classe para redirecionar a saída para o widget Text"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        
    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", string)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")
        
    def flush(self):
        pass

class MySQLConnectionTester(ctk.CTk):
    """Interface gráfica para testar conexões MySQL e pesquisar tabelas"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Teste de Conexão MySQL")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Configurações do tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Configurar credenciais
        setup_mysql_credentials()
        
        # Variáveis para armazenar configurações
        self.local_config = {
            'host': StringVar(value=os.environ.get('MYSQL_LOCAL_HOST', 'localhost')),
            'port': StringVar(value=os.environ.get('MYSQL_LOCAL_PORT', '3306')),
            'user': StringVar(value=os.environ.get('MYSQL_LOCAL_USER', 'root')),
            'password': StringVar(value=os.environ.get('MYSQL_LOCAL_PASSWORD', '')),
            'database': StringVar(value=os.environ.get('MYSQL_LOCAL_DATABASE', 'controlix_local'))
        }
        
        self.remote_config = {
            'host': StringVar(value=os.environ.get('MYSQL_REMOTE_HOST', '')),
            'port': StringVar(value=os.environ.get('MYSQL_REMOTE_PORT', '3306')),
            'user': StringVar(value=os.environ.get('MYSQL_REMOTE_USER', '')),
            'password': StringVar(value=os.environ.get('MYSQL_REMOTE_PASSWORD', '')),
            'database': StringVar(value=os.environ.get('MYSQL_REMOTE_DATABASE', 'controlix_remote'))
        }
        
        # Variáveis para armazenar conexões
        self.local_connection = None
        self.remote_connection = None
        
        # Variáveis para pesquisa
        self.search_table_var = StringVar()
        self.search_column_var = StringVar()
        self.search_value_var = StringVar()
        self.search_db_var = StringVar(value="local")
        
        # Criar interface
        self.create_widgets()
        
        # Carregar configurações iniciais
        self.load_config()
        
        logger.info("Interface gráfica inicializada")

    def create_widgets(self):
        """Cria os widgets da interface gráfica"""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Notebook para abas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Aba de configuração
        config_frame = ctk.CTkFrame(notebook)
        notebook.add(config_frame, text="Configuração")
        
        # Aba de pesquisa
        search_frame = ctk.CTkFrame(notebook)
        notebook.add(search_frame, text="Pesquisa")
        
        # Aba de comparação
        compare_frame = ctk.CTkFrame(notebook)
        notebook.add(compare_frame, text="Comparação")
        
        # Aba de resultados
        results_frame = ctk.CTkFrame(notebook)
        notebook.add(results_frame, text="Resultados")
        
        # Configuração do banco local
        local_frame = ctk.CTkFrame(config_frame)
        local_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(local_frame, text="Configuração do Banco Local", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Host
        host_frame = ctk.CTkFrame(local_frame)
        host_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(host_frame, text="Host:", width=100).pack(side="left")
        ctk.CTkEntry(host_frame, textvariable=self.local_config['host'], width=200).pack(side="left", padx=5)
        
        # Port
        port_frame = ctk.CTkFrame(local_frame)
        port_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(port_frame, text="Porta:", width=100).pack(side="left")
        ctk.CTkEntry(port_frame, textvariable=self.local_config['port'], width=200).pack(side="left", padx=5)
        
        # User
        user_frame = ctk.CTkFrame(local_frame)
        user_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(user_frame, text="Usuário:", width=100).pack(side="left")
        ctk.CTkEntry(user_frame, textvariable=self.local_config['user'], width=200).pack(side="left", padx=5)
        
        # Password
        password_frame = ctk.CTkFrame(local_frame)
        password_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(password_frame, text="Senha:", width=100).pack(side="left")
        ctk.CTkEntry(password_frame, textvariable=self.local_config['password'], width=200, show="*").pack(side="left", padx=5)
        
        # Database
        database_frame = ctk.CTkFrame(local_frame)
        database_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(database_frame, text="Banco:", width=100).pack(side="left")
        ctk.CTkEntry(database_frame, textvariable=self.local_config['database'], width=200).pack(side="left", padx=5)
        
        # Botão de teste
        test_local_button = ctk.CTkButton(local_frame, text="Testar Conexão Local", command=lambda: self.test_connection(is_local=True))
        test_local_button.pack(pady=10)
        
        # Configuração do banco remoto
        remote_frame = ctk.CTkFrame(config_frame)
        remote_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(remote_frame, text="Configuração do Banco Remoto", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Host
        host_frame = ctk.CTkFrame(remote_frame)
        host_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(host_frame, text="Host:", width=100).pack(side="left")
        ctk.CTkEntry(host_frame, textvariable=self.remote_config['host'], width=200).pack(side="left", padx=5)
        
        # Port
        port_frame = ctk.CTkFrame(remote_frame)
        port_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(port_frame, text="Porta:", width=100).pack(side="left")
        ctk.CTkEntry(port_frame, textvariable=self.remote_config['port'], width=200).pack(side="left", padx=5)
        
        # User
        user_frame = ctk.CTkFrame(remote_frame)
        user_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(user_frame, text="Usuário:", width=100).pack(side="left")
        ctk.CTkEntry(user_frame, textvariable=self.remote_config['user'], width=200).pack(side="left", padx=5)
        
        # Password
        password_frame = ctk.CTkFrame(remote_frame)
        password_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(password_frame, text="Senha:", width=100).pack(side="left")
        ctk.CTkEntry(password_frame, textvariable=self.remote_config['password'], width=200, show="*").pack(side="left", padx=5)
        
        # Database
        database_frame = ctk.CTkFrame(remote_frame)
        database_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(database_frame, text="Banco:", width=100).pack(side="left")
        ctk.CTkEntry(database_frame, textvariable=self.remote_config['database'], width=200).pack(side="left", padx=5)
        
        # Botão de teste
        test_remote_button = ctk.CTkButton(remote_frame, text="Testar Conexão Remota", command=lambda: self.test_connection(is_local=False))
        test_remote_button.pack(pady=10)
        
        # Frame de pesquisa
        search_controls_frame = ctk.CTkFrame(search_frame)
        search_controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Seleção de banco
        db_frame = ctk.CTkFrame(search_controls_frame)
        db_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(db_frame, text="Banco:", width=100).pack(side="left")
        ctk.CTkRadioButton(db_frame, text="Local", variable=self.search_db_var, value="local").pack(side="left", padx=5)
        ctk.CTkRadioButton(db_frame, text="Remoto", variable=self.search_db_var, value="remote").pack(side="left", padx=5)
        
        # Nome da tabela
        table_frame = ctk.CTkFrame(search_controls_frame)
        table_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(table_frame, text="Tabela:", width=100).pack(side="left")
        self.table_entry = ctk.CTkEntry(table_frame, textvariable=self.search_table_var, width=200)
        self.table_entry.pack(side="left", padx=5)
        
        # Botão para listar tabelas
        list_tables_button = ctk.CTkButton(table_frame, text="Listar Tabelas", command=self.list_tables)
        list_tables_button.pack(side="left", padx=5)
        
        # Coluna (opcional)
        column_frame = ctk.CTkFrame(search_controls_frame)
        column_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(column_frame, text="Coluna:", width=100).pack(side="left")
        self.column_entry = ctk.CTkEntry(column_frame, textvariable=self.search_column_var, width=200)
        self.column_entry.pack(side="left", padx=5)
        
        # Botão para listar colunas
        list_columns_button = ctk.CTkButton(column_frame, text="Listar Colunas", command=self.list_columns)
        list_columns_button.pack(side="left", padx=5)
        
        # Valor de pesquisa (opcional)
        value_frame = ctk.CTkFrame(search_controls_frame)
        value_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(value_frame, text="Valor:", width=100).pack(side="left")
        ctk.CTkEntry(value_frame, textvariable=self.search_value_var, width=200).pack(side="left", padx=5)
        
        # Botões de pesquisa
        buttons_frame = ctk.CTkFrame(search_controls_frame)
        buttons_frame.pack(fill="x", padx=10, pady=10)
        
        search_button = ctk.CTkButton(buttons_frame, text="Pesquisar", command=self.search_table)
        search_button.pack(side="left", padx=5)
        
        clear_button = ctk.CTkButton(buttons_frame, text="Limpar", command=self.clear_search)
        clear_button.pack(side="left", padx=5)
        
        # Frame de comparação
        compare_controls_frame = ctk.CTkFrame(compare_frame)
        compare_controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Título
        ctk.CTkLabel(compare_controls_frame, text="Comparação entre Bancos Local e Remoto", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Botões de comparação
        compare_buttons_frame = ctk.CTkFrame(compare_controls_frame)
        compare_buttons_frame.pack(fill="x", padx=10, pady=10)
        
        compare_tables_button = ctk.CTkButton(compare_buttons_frame, text="Comparar Tabelas", command=self.compare_tables)
        compare_tables_button.pack(side="left", padx=5)
        
        compare_structure_button = ctk.CTkButton(compare_buttons_frame, text="Comparar Estrutura", command=self.compare_table_structure)
        compare_structure_button.pack(side="left", padx=5)
        
        compare_data_button = ctk.CTkButton(compare_buttons_frame, text="Comparar Dados", command=self.compare_table_data)
        compare_data_button.pack(side="left", padx=5)
        
        # Área de resultados
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap="word", height=20)
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.results_text.configure(state="disabled")
        
        # Redirecionar saída para o widget de texto
        self.text_redirect = RedirectText(self.results_text)
        sys.stdout = self.text_redirect
        
        # Barra de status
        self.status_var = StringVar(value="Pronto")
        status_bar = ctk.CTkLabel(main_frame, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill="x", padx=5, pady=5)

    def load_config(self):
        """Carrega as configurações iniciais"""
        try:
            logger.info("Carregando configurações iniciais")
            
            # Exibir configurações carregadas
            print("Configurações do banco local:")
            print(f"  Host: {self.local_config['host'].get()}")
            print(f"  Porta: {self.local_config['port'].get()}")
            print(f"  Usuário: {self.local_config['user'].get()}")
            print(f"  Banco: {self.local_config['database'].get()}")
            
            print("\nConfigurações do banco remoto:")
            print(f"  Host: {self.remote_config['host'].get()}")
            print(f"  Porta: {self.remote_config['port'].get()}")
            print(f"  Usuário: {self.remote_config['user'].get()}")
            print(f"  Banco: {self.remote_config['database'].get()}")
            
            self.status_var.set("Configurações carregadas")
            logger.info("Configurações carregadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            self.display_error(f"Erro ao carregar configurações: {e}")
    
    def test_connection(self, is_local=True):
        """Testa a conexão com o banco de dados"""
        try:
            # Atualizar status
            self.status_var.set(f"Testando conexão com o banco {'local' if is_local else 'remoto'}...")
            
            # Obter configurações
            config = self.local_config if is_local else self.remote_config
            
            # Exibir informações
            print(f"\n{'='*50}")
            print(f"Testando conexão com o banco {'local' if is_local else 'remoto'}")
            print(f"{'='*50}")
            print(f"Host: {config['host'].get()}")
            print(f"Porta: {config['port'].get()}")
            print(f"Usuário: {config['user'].get()}")
            print(f"Banco: {config['database'].get()}")
            
            # Criar conexão
            connection = mysql.connector.connect(
                host=config['host'].get(),
                port=int(config['port'].get()),
                user=config['user'].get(),
                password=config['password'].get(),
                database=config['database'].get(),
                charset='utf8mb4',
                use_pure=True,
                autocommit=False,
                connection_timeout=10
            )
            
            # Armazenar conexão
            if is_local:
                self.local_connection = connection
            else:
                self.remote_connection = connection
            
            # Testar execução de consulta
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            cursor.close()
            
            # Exibir resultado
            print(f"\nConexão estabelecida com sucesso!")
            print(f"Versão do MySQL: {result['version']}")
            
            # Listar tabelas
            self.list_tables_for_connection(connection, is_local)
            
            # Atualizar status
            self.status_var.set(f"Conexão com o banco {'local' if is_local else 'remoto'} estabelecida")
            logger.info(f"Conexão com o banco {'local' if is_local else 'remoto'} estabelecida")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco {'local' if is_local else 'remoto'}: {e}")
            self.display_error(f"Erro ao conectar ao banco {'local' if is_local else 'remoto'}: {e}")
            
            # Atualizar status
            self.status_var.set(f"Falha na conexão com o banco {'local' if is_local else 'remoto'}")
            
            return False
    
    def list_tables_for_connection(self, connection, is_local=True):
        """Lista as tabelas disponíveis no banco de dados"""
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            cursor.close()
            
            # Exibir tabelas
            print(f"\nTabelas disponíveis no banco {'local' if is_local else 'remoto'}:")
            for i, table in enumerate(tables):
                table_name = list(table.values())[0]
                print(f"  {i+1}. {table_name}")
            
            return tables
        except Exception as e:
            logger.error(f"Erro ao listar tabelas: {e}")
            self.display_error(f"Erro ao listar tabelas: {e}")
            return []

    def list_tables(self):
        """Lista todas as tabelas do banco selecionado"""
        try:
            # Verificar qual banco está selecionado
            is_local = self.search_db_var.get() == "local"
            
            # Verificar se há conexão
            connection = self.local_connection if is_local else self.remote_connection
            if not connection:
                raise Exception(f"Não há conexão com o banco {'local' if is_local else 'remoto'}")
            
            # Listar tabelas
            tables = self.list_tables_for_connection(connection, is_local)
            
            # Atualizar status
            self.status_var.set(f"Tabelas listadas do banco {'local' if is_local else 'remoto'}")
            
            return tables
        except Exception as e:
            logger.error(f"Erro ao listar tabelas: {e}")
            self.display_error(f"Erro ao listar tabelas: {e}")
            return []
    
    def list_columns(self):
        """Lista as colunas da tabela especificada"""
        try:
            # Verificar qual banco está selecionado
            is_local = self.search_db_var.get() == "local"
            
            # Verificar se há conexão
            connection = self.local_connection if is_local else self.remote_connection
            if not connection:
                raise Exception(f"Não há conexão com o banco {'local' if is_local else 'remoto'}")
            
            # Verificar se há tabela especificada
            table_name = self.search_table_var.get()
            if not table_name:
                raise Exception("Nenhuma tabela especificada")
            
            # Listar colunas
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()
            cursor.close()
            
            # Exibir colunas
            print(f"\nColunas da tabela '{table_name}' no banco {'local' if is_local else 'remoto'}:")
            for i, column in enumerate(columns):
                print(f"  {i+1}. {column['Field']} ({column['Type']}) {' - Chave primária' if column['Key'] == 'PRI' else ''}")
            
            # Atualizar status
            self.status_var.set(f"Colunas listadas da tabela '{table_name}'")
            
            return columns
        except Exception as e:
            logger.error(f"Erro ao listar colunas: {e}")
            self.display_error(f"Erro ao listar colunas: {e}")
            return []
    
    def search_table(self):
        """Pesquisa dados na tabela especificada"""
        try:
            # Verificar qual banco está selecionado
            is_local = self.search_db_var.get() == "local"
            
            # Verificar se há conexão
            connection = self.local_connection if is_local else self.remote_connection
            if not connection:
                raise Exception(f"Não há conexão com o banco {'local' if is_local else 'remoto'}")
            
            # Verificar se há tabela especificada
            table_name = self.search_table_var.get()
            if not table_name:
                raise Exception("Nenhuma tabela especificada")
            
            # Construir consulta
            query = f"SELECT * FROM {table_name}"
            params = []
            
            # Adicionar filtro se houver coluna e valor especificados
            column = self.search_column_var.get()
            value = self.search_value_var.get()
            if column and value:
                query += f" WHERE {column} LIKE %s"
                params.append(f"%{value}%")
            
            # Limitar resultados
            query += " LIMIT 100"
            
            # Executar consulta
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            
            # Exibir resultados
            print(f"\nResultados da pesquisa na tabela '{table_name}' no banco {'local' if is_local else 'remoto'}:")
            print(f"Consulta: {query}")
            print(f"Parâmetros: {params}")
            print(f"Total de registros: {len(results)}")
            
            if results:
                # Exibir cabeçalho
                headers = list(results[0].keys())
                header_str = " | ".join(headers)
                print(f"\n{header_str}")
                print("-" * len(header_str))
                
                # Exibir dados
                for row in results:
                    row_values = []
                    for key in headers:
                        value = row[key]
                        if value is None:
                            row_values.append("NULL")
                        elif isinstance(value, (int, float)):
                            row_values.append(str(value))
                        else:
                            row_values.append(str(value)[:30])
                    print(" | ".join(row_values))
            else:
                print("Nenhum resultado encontrado")
            
            # Atualizar status
            self.status_var.set(f"Pesquisa concluída: {len(results)} registros encontrados")
            
            return results
        except Exception as e:
            logger.error(f"Erro ao pesquisar tabela: {e}")
            self.display_error(f"Erro ao pesquisar tabela: {e}")
            return []
    
    def clear_search(self):
        """Limpa os campos de pesquisa"""
        self.search_table_var.set("")
        self.search_column_var.set("")
        self.search_value_var.set("")
        self.status_var.set("Campos de pesquisa limpos")
        
    def display_error(self, error):
        """Exibe uma mensagem de erro"""
        print(f"\nERRO: {error}")
        messagebox.showerror("Erro", str(error))

    def run(self):
        """Executa a aplicação"""
        logger.info("Iniciando aplicação")
        self.mainloop()
    
    def close(self):
        """Fecha a aplicação"""
        try:
            # Fechar conexões
            if self.local_connection:
                self.local_connection.close()
                logger.info("Conexão local fechada")
            
            if self.remote_connection:
                self.remote_connection.close()
                logger.info("Conexão remota fechada")
            
            # Restaurar saída padrão
            sys.stdout = sys.__stdout__
            
            # Fechar aplicação
            self.destroy()
            logger.info("Aplicação encerrada")
        except Exception as e:
            logger.error(f"Erro ao fechar aplicação: {e}")

    def compare_tables(self):
        """Compara as tabelas existentes nos bancos local e remoto"""
        try:
            # Verificar se há conexões
            if not self.local_connection or not self.remote_connection:
                raise Exception("É necessário estabelecer conexão com ambos os bancos")
            
            # Obter tabelas do banco local
            cursor_local = self.local_connection.cursor(dictionary=True)
            cursor_local.execute("SHOW TABLES")
            local_tables = [list(table.values())[0] for table in cursor_local.fetchall()]
            cursor_local.close()
            
            # Obter tabelas do banco remoto
            cursor_remote = self.remote_connection.cursor(dictionary=True)
            cursor_remote.execute("SHOW TABLES")
            remote_tables = [list(table.values())[0] for table in cursor_remote.fetchall()]
            cursor_remote.close()
            
            # Comparar tabelas
            local_only = set(local_tables) - set(remote_tables)
            remote_only = set(remote_tables) - set(local_tables)
            common = set(local_tables).intersection(set(remote_tables))
            
            # Exibir resultados
            print(f"\n{'='*50}")
            print("COMPARAÇÃO DE TABELAS")
            print(f"{'='*50}")
            print(f"Total de tabelas no banco local: {len(local_tables)}")
            print(f"Total de tabelas no banco remoto: {len(remote_tables)}")
            print(f"Tabelas em comum: {len(common)}")
            
            if local_only:
                print(f"\nTabelas existentes APENAS no banco local ({len(local_only)}):")
                for i, table in enumerate(sorted(local_only)):
                    print(f"  {i+1}. {table}")
            
            if remote_only:
                print(f"\nTabelas existentes APENAS no banco remoto ({len(remote_only)}):")
                for i, table in enumerate(sorted(remote_only)):
                    print(f"  {i+1}. {table}")
            
            print(f"\nTabelas em comum ({len(common)}):")
            for i, table in enumerate(sorted(common)):
                print(f"  {i+1}. {table}")
            
            # Atualizar status
            self.status_var.set(f"Comparação de tabelas concluída: {len(common)} tabelas em comum")
            
            return {
                'local_tables': local_tables,
                'remote_tables': remote_tables,
                'local_only': local_only,
                'remote_only': remote_only,
                'common': common
            }
        except Exception as e:
            logger.error(f"Erro ao comparar tabelas: {e}")
            self.display_error(f"Erro ao comparar tabelas: {e}")
            return None
    
    def compare_table_structure(self):
        """Compara a estrutura de uma tabela específica entre os bancos local e remoto"""
        try:
            # Verificar se há conexões
            if not self.local_connection or not self.remote_connection:
                raise Exception("É necessário estabelecer conexão com ambos os bancos")
            
            # Obter nome da tabela
            table_name = self.search_table_var.get()
            if not table_name:
                raise Exception("É necessário especificar uma tabela para comparação")
            
            # Verificar se a tabela existe em ambos os bancos
            cursor_local = self.local_connection.cursor(dictionary=True)
            cursor_local.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor_local.fetchone():
                cursor_local.close()
                raise Exception(f"A tabela '{table_name}' não existe no banco local")
            
            cursor_remote = self.remote_connection.cursor(dictionary=True)
            cursor_remote.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor_remote.fetchone():
                cursor_local.close()
                cursor_remote.close()
                raise Exception(f"A tabela '{table_name}' não existe no banco remoto")
            
            # Obter estrutura da tabela local
            cursor_local.execute(f"DESCRIBE {table_name}")
            local_columns = cursor_local.fetchall()
            cursor_local.close()
            
            # Obter estrutura da tabela remota
            cursor_remote.execute(f"DESCRIBE {table_name}")
            remote_columns = cursor_remote.fetchall()
            cursor_remote.close()
            
            # Comparar estruturas
            local_column_names = [col['Field'] for col in local_columns]
            remote_column_names = [col['Field'] for col in remote_columns]
            
            local_only = set(local_column_names) - set(remote_column_names)
            remote_only = set(remote_column_names) - set(local_column_names)
            common = set(local_column_names).intersection(set(remote_column_names))
            
            # Criar dicionários para facilitar a comparação
            local_dict = {col['Field']: col for col in local_columns}
            remote_dict = {col['Field']: col for col in remote_columns}
            
            # Exibir resultados
            print(f"\n{'='*50}")
            print(f"COMPARAÇÃO DE ESTRUTURA DA TABELA '{table_name}'")
            print(f"{'='*50}")
            print(f"Total de colunas no banco local: {len(local_columns)}")
            print(f"Total de colunas no banco remoto: {len(remote_columns)}")
            print(f"Colunas em comum: {len(common)}")
            
            if local_only:
                print(f"\nColunas existentes APENAS no banco local ({len(local_only)}):")
                for i, col in enumerate(sorted(local_only)):
                    print(f"  {i+1}. {col} - {local_dict[col]['Type']} {local_dict[col]['Null']} {local_dict[col]['Key']}")
            
            if remote_only:
                print(f"\nColunas existentes APENAS no banco remoto ({len(remote_only)}):")
                for i, col in enumerate(sorted(remote_only)):
                    print(f"  {i+1}. {col} - {remote_dict[col]['Type']} {remote_dict[col]['Null']} {remote_dict[col]['Key']}")
            
            print(f"\nColunas em comum ({len(common)}):")
            for i, col in enumerate(sorted(common)):
                local_type = local_dict[col]['Type']
                remote_type = remote_dict[col]['Type']
                local_null = local_dict[col]['Null']
                remote_null = remote_dict[col]['Null']
                local_key = local_dict[col]['Key']
                remote_key = remote_dict[col]['Key']
                
                # Verificar diferenças
                type_diff = local_type != remote_type
                null_diff = local_null != remote_null
                key_diff = local_key != remote_key
                
                if type_diff or null_diff or key_diff:
                    print(f"  {i+1}. {col} - DIFERENÇAS ENCONTRADAS:")
                    if type_diff:
                        print(f"     Tipo: Local={local_type}, Remoto={remote_type}")
                    if null_diff:
                        print(f"     Null: Local={local_null}, Remoto={remote_null}")
                    if key_diff:
                        print(f"     Key: Local={local_key}, Remoto={remote_key}")
                else:
                    print(f"  {i+1}. {col} - {local_type} {local_null} {local_key} (idêntico)")
            
            # Atualizar status
            self.status_var.set(f"Comparação de estrutura concluída: {len(common)} colunas em comum")
            
            return {
                'local_columns': local_columns,
                'remote_columns': remote_columns,
                'local_only': local_only,
                'remote_only': remote_only,
                'common': common
            }
        except Exception as e:
            logger.error(f"Erro ao comparar estrutura da tabela: {e}")
            self.display_error(f"Erro ao comparar estrutura da tabela: {e}")
            return None
    
    def compare_table_data(self):
        """Compara os dados de uma tabela específica entre os bancos local e remoto"""
        try:
            # Verificar se há conexões
            if not self.local_connection or not self.remote_connection:
                raise Exception("É necessário estabelecer conexão com ambos os bancos")
            
            # Obter nome da tabela
            table_name = self.search_table_var.get()
            if not table_name:
                raise Exception("É necessário especificar uma tabela para comparação")
            
            # Verificar se a tabela existe em ambos os bancos
            cursor_local = self.local_connection.cursor(dictionary=True)
            cursor_local.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor_local.fetchone():
                cursor_local.close()
                raise Exception(f"A tabela '{table_name}' não existe no banco local")
            
            cursor_remote = self.remote_connection.cursor(dictionary=True)
            cursor_remote.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor_remote.fetchone():
                cursor_local.close()
                cursor_remote.close()
                raise Exception(f"A tabela '{table_name}' não existe no banco remoto")
            
            # Obter chave primária da tabela
            cursor_local.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
            primary_key = cursor_local.fetchone()
            if not primary_key:
                cursor_local.close()
                cursor_remote.close()
                raise Exception(f"A tabela '{table_name}' não possui chave primária")
            
            primary_key_column = primary_key['Column_name']
            
            # Obter contagem de registros
            cursor_local.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            local_count = cursor_local.fetchone()['count']
            
            cursor_remote.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            remote_count = cursor_remote.fetchone()['count']
            
            # Obter dados (limitado a 1000 registros para evitar sobrecarga)
            cursor_local.execute(f"SELECT * FROM {table_name} ORDER BY {primary_key_column} LIMIT 1000")
            local_data = cursor_local.fetchall()
            
            cursor_remote.execute(f"SELECT * FROM {table_name} ORDER BY {primary_key_column} LIMIT 1000")
            remote_data = cursor_remote.fetchall()
            
            # Criar dicionários para facilitar a comparação
            local_dict = {str(row[primary_key_column]): row for row in local_data}
            remote_dict = {str(row[primary_key_column]): row for row in remote_data}
            
            # Comparar dados
            local_keys = set(local_dict.keys())
            remote_keys = set(remote_dict.keys())
            
            local_only = local_keys - remote_keys
            remote_only = remote_keys - local_keys
            common = local_keys.intersection(remote_keys)
            
            # Verificar diferenças nos registros comuns
            different = []
            for key in common:
                local_row = local_dict[key]
                remote_row = remote_dict[key]
                
                # Comparar valores
                if local_row != remote_row:
                    different.append(key)
            
            # Exibir resultados
            print(f"\n{'='*50}")
            print(f"COMPARAÇÃO DE DADOS DA TABELA '{table_name}'")
            print(f"{'='*50}")
            print(f"Total de registros no banco local: {local_count}")
            print(f"Total de registros no banco remoto: {remote_count}")
            print(f"Registros analisados: {len(local_data)} (local), {len(remote_data)} (remoto)")
            print(f"Chave primária: {primary_key_column}")
            
            print(f"\nResultados da comparação:")
            print(f"  Registros existentes apenas no banco local: {len(local_only)}")
            print(f"  Registros existentes apenas no banco remoto: {len(remote_only)}")
            print(f"  Registros em comum: {len(common)}")
            print(f"  Registros com diferenças: {len(different)}")
            
            # Exibir alguns exemplos de diferenças (limitado a 10)
            if different:
                print(f"\nExemplos de registros com diferenças:")
                for i, key in enumerate(list(different)[:10]):
                    local_row = local_dict[key]
                    remote_row = remote_dict[key]
                    
                    print(f"\n  {i+1}. Registro com {primary_key_column}={key}:")
                    
                    # Encontrar colunas com diferenças
                    diff_columns = []
                    for col in local_row.keys():
                        if local_row[col] != remote_row[col]:
                            diff_columns.append(col)
                    
                    # Exibir apenas as colunas com diferenças
                    for col in diff_columns:
                        local_val = local_row[col]
                        remote_val = remote_row[col]
                        print(f"     {col}: Local='{local_val}', Remoto='{remote_val}'")
            
            # Atualizar status
            self.status_var.set(f"Comparação de dados concluída: {len(different)} registros com diferenças")
            
            return {
                'local_count': local_count,
                'remote_count': remote_count,
                'local_only': local_only,
                'remote_only': remote_only,
                'common': common,
                'different': different
            }
        except Exception as e:
            logger.error(f"Erro ao comparar dados da tabela: {e}")
            self.display_error(f"Erro ao comparar dados da tabela: {e}")
            return None

def main():
    """Função principal"""
    try:
        # Criar e executar aplicação
        app = MySQLConnectionTester()
        app.protocol("WM_DELETE_WINDOW", app.close)
        app.run()
    except Exception as e:
        logger.error(f"Erro na aplicação: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

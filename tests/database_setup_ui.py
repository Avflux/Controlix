#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface gráfica para configuração de bancos de dados.
Permite inserir tabelas e colunas padrão no MySQL e SQLite.
"""

import os
import sys
import logging
import sqlite3
import mysql.connector
from pathlib import Path
import threading
import tempfile
import time
import customtkinter as ctk
from tkinter import messagebox, scrolledtext
import traceback

# Adiciona o diretório raiz ao path para importações
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from app.config.settings import SQLITE_DIR, DATABASE
from app.data.connection import DatabaseConnection
from app.data.sync.sync_manager import DEFAULT_TABLES

# Configuração de logging
log_file = 'logs/database_setup_detailed.log'
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)

logger = logging.getLogger('database_setup')
logger.info("="*50)
logger.info("INICIANDO APLICAÇÃO DE CONFIGURAÇÃO DE BANCOS DE DADOS")
logger.info("="*50)

class RedirectText:
    """Classe para redirecionar a saída para o widget Text"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        self.terminal = sys.__stdout__
        self.log_file = open('logs/database_setup_ui.log', 'a', encoding='utf-8')
        self.log_file.write("\n" + "="*50 + "\n")
        self.log_file.write("NOVA SESSÃO: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        self.log_file.write("="*50 + "\n")
        
    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", string)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")
        # Também escreve no terminal original e no arquivo de log
        self.terminal.write(string)
        self.log_file.write(string)
        self.log_file.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        
    def __del__(self):
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()

class DatabaseSetupApp(ctk.CTk):
    """Interface gráfica para configuração de bancos de dados"""
    
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Configuração de Bancos de Dados")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # Configuração do tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variáveis
        self.is_running = False
        self.db_conn = None
        
        # Criar widgets
        self._create_widgets()
        
        # Inicializar conexão com banco de dados
        self._init_db_connection()
    
    def _create_widgets(self):
        """Cria os widgets da interface"""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Configuração de Bancos de Dados",
            font=("Roboto", 24, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Descrição
        self.desc_label = ctk.CTkLabel(
            self.main_frame,
            text="Esta ferramenta permite inserir tabelas e colunas padrão no MySQL e SQLite.",
            font=("Roboto", 14)
        )
        self.desc_label.pack(pady=5)
        
        # Frame de botões
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", padx=20, pady=20)
        
        # Botões para MySQL
        self.mysql_label = ctk.CTkLabel(
            self.button_frame,
            text="MySQL",
            font=("Roboto", 16, "bold")
        )
        self.mysql_label.grid(row=0, column=0, pady=5, padx=10, sticky="w")
        
        self.check_mysql_btn = ctk.CTkButton(
            self.button_frame,
            text="Verificar Tabelas MySQL",
            command=self._check_mysql_tables,
            width=200
        )
        self.check_mysql_btn.grid(row=1, column=0, pady=5, padx=10)
        
        self.create_mysql_tables_btn = ctk.CTkButton(
            self.button_frame,
            text="Criar Tabelas MySQL",
            command=self._create_mysql_tables,
            width=200
        )
        self.create_mysql_tables_btn.grid(row=2, column=0, pady=5, padx=10)
        
        self.add_mysql_columns_btn = ctk.CTkButton(
            self.button_frame,
            text="Adicionar Colunas MySQL",
            command=self._add_mysql_columns,
            width=200
        )
        self.add_mysql_columns_btn.grid(row=3, column=0, pady=5, padx=10)
        
        self.show_mysql_structure_btn = ctk.CTkButton(
            self.button_frame,
            text="Mostrar Estrutura MySQL",
            command=self._show_mysql_structure,
            width=200
        )
        self.show_mysql_structure_btn.grid(row=4, column=0, pady=5, padx=10)
        
        # Botões para SQLite
        self.sqlite_label = ctk.CTkLabel(
            self.button_frame,
            text="SQLite",
            font=("Roboto", 16, "bold")
        )
        self.sqlite_label.grid(row=0, column=1, pady=5, padx=10, sticky="w")
        
        self.check_sqlite_btn = ctk.CTkButton(
            self.button_frame,
            text="Verificar Tabelas SQLite",
            command=self._check_sqlite_tables,
            width=200
        )
        self.check_sqlite_btn.grid(row=1, column=1, pady=5, padx=10)
        
        self.create_sqlite_tables_btn = ctk.CTkButton(
            self.button_frame,
            text="Criar Tabelas SQLite",
            command=self._create_sqlite_tables,
            width=200
        )
        self.create_sqlite_tables_btn.grid(row=2, column=1, pady=5, padx=10)
        
        self.add_sqlite_columns_btn = ctk.CTkButton(
            self.button_frame,
            text="Adicionar Colunas SQLite",
            command=self._add_sqlite_columns,
            width=200
        )
        self.add_sqlite_columns_btn.grid(row=3, column=1, pady=5, padx=10)
        
        self.show_sqlite_structure_btn = ctk.CTkButton(
            self.button_frame,
            text="Mostrar Estrutura SQLite",
            command=self._show_sqlite_structure,
            width=200
        )
        self.show_sqlite_structure_btn.grid(row=4, column=1, pady=5, padx=10)
        
        # Botão para verificar tudo
        self.check_all_btn = ctk.CTkButton(
            self.button_frame,
            text="Verificar Todos os Bancos",
            command=self._check_all_databases,
            width=200,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.check_all_btn.grid(row=5, column=0, pady=10, padx=10)
        
        # Botão para criar tudo
        self.create_all_btn = ctk.CTkButton(
            self.button_frame,
            text="Criar Todas as Tabelas",
            command=self._create_all_tables,
            width=200,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.create_all_btn.grid(row=5, column=1, pady=10, padx=10)
        
        # Botão para gerar relatório
        self.report_btn = ctk.CTkButton(
            self.button_frame,
            text="Gerar Relatório Completo",
            command=self._generate_report,
            width=410,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.report_btn.grid(row=6, column=0, pady=10, padx=10, columnspan=2)
        
        # Configuração do grid
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        
        # Área de log
        self.log_label = ctk.CTkLabel(
            self.main_frame,
            text="Log de Operações",
            font=("Roboto", 16, "bold")
        )
        self.log_label.pack(pady=(20, 5), anchor="w", padx=20)
        
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap="word",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.configure(state="disabled")
        
        # Redirecionar saída para o widget de log
        self.text_redirect = RedirectText(self.log_text)
        sys.stdout = self.text_redirect
        sys.stderr = self.text_redirect
    
    def _init_db_connection(self):
        """Inicializa a conexão com o banco de dados"""
        try:
            self.db_conn = DatabaseConnection()
            print("Conexão com o banco de dados inicializada com sucesso.")
        except Exception as e:
            print(f"Erro ao inicializar conexão com o banco de dados: {e}")
            messagebox.showerror("Erro", f"Erro ao inicializar conexão com o banco de dados: {e}")
    
    def _run_in_thread(self, func):
        """Executa uma função em uma thread separada"""
        if self.is_running:
            messagebox.showwarning("Aviso", "Uma operação já está em andamento. Aguarde a conclusão.")
            return
        
        self.is_running = True
        self._disable_buttons()
        
        thread = threading.Thread(target=self._thread_wrapper, args=(func,))
        thread.daemon = True
        thread.start()
    
    def _thread_wrapper(self, func):
        """Wrapper para executar função em thread e lidar com exceções"""
        try:
            func()
        except Exception as e:
            print(f"Erro: {e}")
            print(traceback.format_exc())
            self.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro: {e}"))
        finally:
            self.is_running = False
            self.after(0, self._enable_buttons)
    
    def _disable_buttons(self):
        """Desabilita os botões durante a execução de uma operação"""
        self.check_mysql_btn.configure(state="disabled")
        self.create_mysql_tables_btn.configure(state="disabled")
        self.add_mysql_columns_btn.configure(state="disabled")
        self.show_mysql_structure_btn.configure(state="disabled")
        self.check_sqlite_btn.configure(state="disabled")
        self.create_sqlite_tables_btn.configure(state="disabled")
        self.add_sqlite_columns_btn.configure(state="disabled")
        self.show_sqlite_structure_btn.configure(state="disabled")
        self.check_all_btn.configure(state="disabled")
        self.create_all_btn.configure(state="disabled")
        self.report_btn.configure(state="disabled")
    
    def _enable_buttons(self):
        """Habilita os botões após a conclusão de uma operação"""
        self.check_mysql_btn.configure(state="normal")
        self.create_mysql_tables_btn.configure(state="normal")
        self.add_mysql_columns_btn.configure(state="normal")
        self.show_mysql_structure_btn.configure(state="normal")
        self.check_sqlite_btn.configure(state="normal")
        self.create_sqlite_tables_btn.configure(state="normal")
        self.add_sqlite_columns_btn.configure(state="normal")
        self.show_sqlite_structure_btn.configure(state="normal")
        self.check_all_btn.configure(state="normal")
        self.create_all_btn.configure(state="normal")
        self.report_btn.configure(state="normal")
    
    def _check_mysql_tables(self):
        """Verifica as tabelas no MySQL"""
        self._run_in_thread(self._check_mysql_tables_impl)
    
    def _check_mysql_tables_impl(self):
        """Implementação da verificação de tabelas no MySQL"""
        print("\n" + "="*50)
        print("VERIFICANDO TABELAS NO MYSQL")
        print("="*50)
        
        try:
            # Obtém conexão com o banco MySQL
            mysql_conn = self.db_conn.get_mysql_connection()
            
            if not mysql_conn:
                print("Não foi possível conectar ao MySQL")
                return
            
            # Verifica se as tabelas existem
            cursor = mysql_conn.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            print(f"Tabelas existentes no MySQL: {existing_tables}")
            
            # Verifica se as tabelas necessárias existem
            missing_tables = []
            for table_name in DEFAULT_TABLES.keys():
                if table_name not in existing_tables:
                    missing_tables.append(table_name)
            
            # Verifica se as tabelas de controle de sincronização existem
            for table_name in ['sync_log', 'sync_conflicts', 'sync_metadata']:
                if table_name not in existing_tables:
                    missing_tables.append(table_name)
            
            if missing_tables:
                print(f"Tabelas faltando no MySQL: {missing_tables}")
            else:
                print("Todas as tabelas necessárias existem no MySQL.")
            
            # Verifica se as colunas de versionamento existem
            missing_columns_tables = []
            for table_name in DEFAULT_TABLES.keys():
                if table_name in existing_tables:
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = {row[0]: row for row in cursor.fetchall()}
                    
                    missing_columns = []
                    if 'version' not in columns:
                        missing_columns.append('version')
                    if 'last_modified' not in columns:
                        missing_columns.append('last_modified')
                    
                    if missing_columns:
                        print(f"Colunas faltando na tabela {table_name} do MySQL: {missing_columns}")
                        missing_columns_tables.append(table_name)
            
            if not missing_tables and not missing_columns_tables:
                print("Verificação concluída com sucesso. Todas as tabelas e colunas necessárias existem no MySQL.")
            else:
                print("Verificação concluída com avisos. Algumas tabelas ou colunas estão faltando no MySQL.")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao verificar tabelas no MySQL: {e}")
            raise
    
    def _check_sqlite_tables(self):
        """Verifica as tabelas no SQLite"""
        self._run_in_thread(self._check_sqlite_tables_impl)
    
    def _check_sqlite_tables_impl(self):
        """Implementação da verificação de tabelas no SQLite"""
        print("\n" + "="*50)
        print("VERIFICANDO TABELAS NO SQLITE")
        print("="*50)
        
        try:
            # Obtém conexão com o banco SQLite
            sqlite_conn = self.db_conn.get_sqlite_connection()
            
            # Verifica se as tabelas existem
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            print(f"Tabelas existentes no SQLite: {existing_tables}")
            
            # Verifica se as tabelas necessárias existem
            missing_tables = []
            for table_name in DEFAULT_TABLES.keys():
                if table_name not in existing_tables:
                    missing_tables.append(table_name)
            
            # Verifica se as tabelas de controle de sincronização existem
            for table_name in ['sync_log', 'sync_conflicts', 'sync_metadata']:
                if table_name not in existing_tables:
                    missing_tables.append(table_name)
            
            if missing_tables:
                print(f"Tabelas faltando no SQLite: {missing_tables}")
            else:
                print("Todas as tabelas necessárias existem no SQLite.")
            
            # Verifica se as colunas de versionamento existem
            missing_columns_tables = []
            for table_name in DEFAULT_TABLES.keys():
                if table_name in existing_tables:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = {column[1]: column for column in cursor.fetchall()}
                    
                    missing_columns = []
                    if 'version' not in columns:
                        missing_columns.append('version')
                    if 'last_modified' not in columns:
                        missing_columns.append('last_modified')
                    
                    if missing_columns:
                        print(f"Colunas faltando na tabela {table_name} do SQLite: {missing_columns}")
                        missing_columns_tables.append(table_name)
            
            if not missing_tables and not missing_columns_tables:
                print("Verificação concluída com sucesso. Todas as tabelas e colunas necessárias existem no SQLite.")
            else:
                print("Verificação concluída com avisos. Algumas tabelas ou colunas estão faltando no SQLite.")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao verificar tabelas no SQLite: {e}")
            raise
    
    def _check_all_databases(self):
        """Verifica todas as tabelas em todos os bancos"""
        self._run_in_thread(lambda: (self._check_mysql_tables_impl(), self._check_sqlite_tables_impl()))
    
    def _create_mysql_tables(self):
        """Cria as tabelas no MySQL"""
        self._run_in_thread(self._create_mysql_tables_impl)
    
    def _create_mysql_tables_impl(self):
        """Implementação da criação de tabelas no MySQL"""
        print("\n" + "="*50)
        print("CRIANDO TABELAS NO MYSQL")
        print("="*50)
        
        try:
            # Obtém conexão com o banco MySQL
            mysql_conn = self.db_conn.get_mysql_connection()
            
            if not mysql_conn:
                print("Não foi possível conectar ao MySQL")
                return
            
            # Carrega e executa o script de criação de tabelas
            create_tables_sql_path = Path('tests') / 'create_tables.sql'
            
            if not create_tables_sql_path.exists():
                print(f"Arquivo de criação de tabelas não encontrado: {create_tables_sql_path}")
                return
            
            with open(create_tables_sql_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Divide o script em comandos individuais
            commands = []
            current_command = ""
            delimiter = ";"
            
            for line in sql_script.splitlines():
                line = line.strip()
                
                # Ignora linhas vazias e comentários
                if not line or line.startswith('--'):
                    continue
                
                # Verifica se há mudança de delimiter
                if line.upper().startswith("DELIMITER"):
                    if current_command:
                        commands.append(current_command)
                        current_command = ""
                    delimiter = line.split()[1]
                    continue
                
                # Adiciona a linha ao comando atual
                current_command += line + "\n"
                
                # Verifica se o comando terminou
                if line.endswith(delimiter):
                    # Remove o delimiter do final
                    if delimiter != ";":
                        current_command = current_command[:-len(delimiter)]
                    else:
                        current_command = current_command[:-1]
                    
                    commands.append(current_command.strip())
                    current_command = ""
            
            # Adiciona o último comando se houver
            if current_command.strip():
                commands.append(current_command.strip())
            
            # Executa cada comando
            cursor = mysql_conn.cursor()
            
            for i, command in enumerate(commands):
                if not command:
                    continue
                
                try:
                    cursor.execute(command)
                    print(f"Comando {i+1}/{len(commands)} executado com sucesso")
                except mysql.connector.Error as e:
                    print(f"Erro ao executar comando {i+1}/{len(commands)}: {e}")
                    print(f"Comando: {command[:100]}...")
            
            mysql_conn.commit()
            print("Tabelas criadas com sucesso no MySQL")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao criar tabelas no MySQL: {e}")
            raise
    
    def _create_sqlite_tables(self):
        """Cria as tabelas no SQLite"""
        self._run_in_thread(self._create_sqlite_tables_impl)
    
    def _create_sqlite_tables_impl(self):
        """Implementação da criação de tabelas no SQLite"""
        print("\n" + "="*50)
        print("CRIANDO TABELAS NO SQLITE")
        print("="*50)
        
        try:
            # Obtém conexão com o banco SQLite
            sqlite_conn = self.db_conn.get_sqlite_connection()
            
            # Carrega e executa o script de criação de tabelas
            create_tables_sql_path = Path(SQLITE_DIR) / 'create_tables.sql'
            
            if not create_tables_sql_path.exists():
                print(f"Arquivo de criação de tabelas não encontrado: {create_tables_sql_path}")
                return
            
            with open(create_tables_sql_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Executa o script
            cursor = sqlite_conn.cursor()
            cursor.executescript(sql_script)
            sqlite_conn.commit()
            
            print("Tabelas criadas com sucesso no SQLite")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao criar tabelas no SQLite: {e}")
            raise
    
    def _create_all_tables(self):
        """Cria todas as tabelas em todos os bancos"""
        self._run_in_thread(lambda: (self._create_mysql_tables_impl(), self._create_sqlite_tables_impl()))
    
    def _add_mysql_columns(self):
        """Adiciona colunas de versionamento no MySQL"""
        self._run_in_thread(self._add_mysql_columns_impl)
    
    def _add_mysql_columns_impl(self):
        """Implementação da adição de colunas de versionamento no MySQL"""
        print("\n" + "="*50)
        print("ADICIONANDO COLUNAS NO MYSQL")
        print("="*50)
        
        try:
            # Obtém conexão com o banco MySQL
            mysql_conn = self.db_conn.get_mysql_connection()
            
            if not mysql_conn:
                print("Não foi possível conectar ao MySQL")
                return
            
            # Verifica se as tabelas existem
            cursor = mysql_conn.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Adiciona colunas de versionamento
            for table_name in DEFAULT_TABLES.keys():
                if table_name in existing_tables:
                    # Verifica se as colunas já existem
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = {row[0]: row for row in cursor.fetchall()}
                    
                    # Adiciona coluna version se não existir
                    if 'version' not in columns:
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name}
                                ADD COLUMN version INT NOT NULL DEFAULT 1
                            """)
                            print(f"Coluna 'version' adicionada à tabela {table_name}")
                        except mysql.connector.Error as e:
                            print(f"Erro ao adicionar coluna 'version' à tabela {table_name}: {e}")
                    
                    # Adiciona coluna last_modified se não existir
                    if 'last_modified' not in columns:
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name}
                                ADD COLUMN last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            """)
                            print(f"Coluna 'last_modified' adicionada à tabela {table_name}")
                        except mysql.connector.Error as e:
                            print(f"Erro ao adicionar coluna 'last_modified' à tabela {table_name}: {e}")
            
            mysql_conn.commit()
            print("Colunas adicionadas com sucesso no MySQL")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao adicionar colunas no MySQL: {e}")
            raise
    
    def _add_sqlite_columns(self):
        """Adiciona colunas de versionamento no SQLite"""
        self._run_in_thread(self._add_sqlite_columns_impl)
    
    def _add_sqlite_columns_impl(self):
        """Implementação da adição de colunas de versionamento no SQLite"""
        print("\n" + "="*50)
        print("ADICIONANDO COLUNAS NO SQLITE")
        print("="*50)
        
        try:
            # Obtém conexão com o banco SQLite
            sqlite_conn = self.db_conn.get_sqlite_connection()
            
            # Verifica se as tabelas existem
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Adiciona colunas de versionamento
            for table_name in DEFAULT_TABLES.keys():
                if table_name in existing_tables:
                    # Verifica se as colunas já existem
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = {column[1]: column for column in cursor.fetchall()}
                    
                    # Adiciona coluna version se não existir
                    if 'version' not in columns:
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name}
                                ADD COLUMN version INTEGER NOT NULL DEFAULT 1
                            """)
                            print(f"Coluna 'version' adicionada à tabela {table_name}")
                        except sqlite3.Error as e:
                            print(f"Erro ao adicionar coluna 'version' à tabela {table_name}: {e}")
                    
                    # Adiciona coluna last_modified se não existir
                    if 'last_modified' not in columns:
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name}
                                ADD COLUMN last_modified TIMESTAMP NOT NULL DEFAULT (datetime('now', 'localtime'))
                            """)
                            print(f"Coluna 'last_modified' adicionada à tabela {table_name}")
                        except sqlite3.Error as e:
                            print(f"Erro ao adicionar coluna 'last_modified' à tabela {table_name}: {e}")
                    
                    # Cria trigger para atualizar last_modified e version se não existir
                    cursor.execute(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='trigger' AND name='update_{table_name}_version_and_timestamp'
                    """)
                    if not cursor.fetchone():
                        try:
                            cursor.execute(f"""
                                CREATE TRIGGER update_{table_name}_version_and_timestamp
                                AFTER UPDATE ON {table_name}
                                FOR EACH ROW
                                BEGIN
                                    UPDATE {table_name}
                                    SET version = version + 1,
                                        last_modified = datetime('now', 'localtime')
                                    WHERE id = NEW.id;
                                END
                            """)
                            print(f"Trigger 'update_{table_name}_version_and_timestamp' criado")
                        except sqlite3.Error as e:
                            print(f"Erro ao criar trigger para tabela {table_name}: {e}")
            
            sqlite_conn.commit()
            print("Colunas adicionadas com sucesso no SQLite")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao adicionar colunas no SQLite: {e}")
            raise
    
    def _generate_report(self):
        """Gera um relatório completo sobre o estado dos bancos de dados"""
        self._run_in_thread(self._generate_report_impl)
    
    def _generate_report_impl(self):
        """Implementação da geração de relatório"""
        print("\n" + "="*50)
        print("GERANDO RELATÓRIO COMPLETO")
        print("="*50)
        
        report_file = 'logs/database_report.txt'
        report_content = ""
        
        try:
            # Captura a saída para uma string
            from io import StringIO
            string_buffer = StringIO()
            original_stdout = sys.stdout
            sys.stdout = string_buffer
            
            # Cabeçalho do relatório
            print("="*50)
            print("RELATÓRIO DE CONFIGURAÇÃO DE BANCOS DE DADOS")
            print("Data: " + time.strftime("%Y-%m-%d %H:%M:%S"))
            print("="*50 + "\n")
            
            # Verifica MySQL
            print("\n" + "="*50)
            print("VERIFICAÇÃO DO MYSQL")
            print("="*50)
            
            try:
                # Obtém conexão com o banco MySQL
                mysql_conn = self.db_conn.get_mysql_connection()
                
                if not mysql_conn:
                    print("Não foi possível conectar ao MySQL")
                else:
                    # Verifica se as tabelas existem
                    cursor = mysql_conn.cursor()
                    cursor.execute("SHOW TABLES")
                    existing_tables = [row[0] for row in cursor.fetchall()]
                    
                    print(f"Tabelas existentes no MySQL: {existing_tables}")
                    
                    # Verifica se as tabelas necessárias existem
                    missing_tables = []
                    for table_name in DEFAULT_TABLES.keys():
                        if table_name not in existing_tables:
                            missing_tables.append(table_name)
                    
                    # Verifica se as tabelas de controle de sincronização existem
                    for table_name in ['sync_log', 'sync_conflicts', 'sync_metadata']:
                        if table_name not in existing_tables:
                            missing_tables.append(table_name)
                    
                    if missing_tables:
                        print(f"Tabelas faltando no MySQL: {missing_tables}")
                    else:
                        print("Todas as tabelas necessárias existem no MySQL.")
                    
                    # Verifica se as colunas de versionamento existem
                    missing_columns_tables = []
                    for table_name in DEFAULT_TABLES.keys():
                        if table_name in existing_tables:
                            cursor.execute(f"DESCRIBE {table_name}")
                            columns = {row[0]: row for row in cursor.fetchall()}
                            
                            missing_columns = []
                            if 'version' not in columns:
                                missing_columns.append('version')
                            if 'last_modified' not in columns:
                                missing_columns.append('last_modified')
                            
                            if missing_columns:
                                print(f"Colunas faltando na tabela {table_name} do MySQL: {missing_columns}")
                                missing_columns_tables.append(table_name)
                    
                    if not missing_tables and not missing_columns_tables:
                        print("Verificação concluída com sucesso. Todas as tabelas e colunas necessárias existem no MySQL.")
                    else:
                        print("Verificação concluída com avisos. Algumas tabelas ou colunas estão faltando no MySQL.")
                    
                    # Fecha a conexão
                    cursor.close()
                    
            except Exception as e:
                print(f"Erro ao verificar tabelas no MySQL: {e}")
            
            # Verifica SQLite
            print("\n" + "="*50)
            print("VERIFICAÇÃO DO SQLITE")
            print("="*50)
            
            try:
                # Obtém conexão com o banco SQLite
                sqlite_conn = self.db_conn.get_sqlite_connection()
                
                # Verifica se as tabelas existem
                cursor = sqlite_conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                print(f"Tabelas existentes no SQLite: {existing_tables}")
                
                # Verifica se as tabelas necessárias existem
                missing_tables = []
                for table_name in DEFAULT_TABLES.keys():
                    if table_name not in existing_tables:
                        missing_tables.append(table_name)
                
                # Verifica se as tabelas de controle de sincronização existem
                for table_name in ['sync_log', 'sync_conflicts', 'sync_metadata']:
                    if table_name not in existing_tables:
                        missing_tables.append(table_name)
                
                if missing_tables:
                    print(f"Tabelas faltando no SQLite: {missing_tables}")
                else:
                    print("Todas as tabelas necessárias existem no SQLite.")
                
                # Verifica se as colunas de versionamento existem
                missing_columns_tables = []
                for table_name in DEFAULT_TABLES.keys():
                    if table_name in existing_tables:
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = {column[1]: column for column in cursor.fetchall()}
                        
                        missing_columns = []
                        if 'version' not in columns:
                            missing_columns.append('version')
                        if 'last_modified' not in columns:
                            missing_columns.append('last_modified')
                        
                        if missing_columns:
                            print(f"Colunas faltando na tabela {table_name} do SQLite: {missing_columns}")
                            missing_columns_tables.append(table_name)
                
                if not missing_tables and not missing_columns_tables:
                    print("Verificação concluída com sucesso. Todas as tabelas e colunas necessárias existem no SQLite.")
                else:
                    print("Verificação concluída com avisos. Algumas tabelas ou colunas estão faltando no SQLite.")
                
                # Fecha a conexão
                cursor.close()
                
            except Exception as e:
                print(f"Erro ao verificar tabelas no SQLite: {e}")
            
            # Obtém o conteúdo do relatório
            report_content = string_buffer.getvalue()
            
            # Restaura a saída padrão
            sys.stdout = original_stdout
            
            # Salva o relatório em um arquivo
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Exibe o relatório na interface
            print("\n" + "="*50)
            print("CONTEÚDO DO RELATÓRIO")
            print("="*50)
            print(report_content)
            
            print(f"Relatório gerado com sucesso: {report_file}")
            messagebox.showinfo("Relatório Gerado", f"Relatório gerado com sucesso: {report_file}")
            
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            raise
    
    def _show_mysql_structure(self):
        """Mostra a estrutura detalhada das tabelas no MySQL"""
        self._run_in_thread(self._show_mysql_structure_impl)
    
    def _show_mysql_structure_impl(self):
        """Implementação da exibição da estrutura das tabelas no MySQL"""
        print("\n" + "="*50)
        print("ESTRUTURA DAS TABELAS NO MYSQL")
        print("="*50)
        
        try:
            # Obtém conexão com o banco MySQL
            mysql_conn = self.db_conn.get_mysql_connection()
            
            if not mysql_conn:
                print("Não foi possível conectar ao MySQL")
                return
            
            # Obtém a lista de tabelas
            cursor = mysql_conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Para cada tabela, mostra a estrutura
            for table in tables:
                print("\n" + "-"*50)
                print(f"TABELA: {table}")
                print("-"*50)
                
                # Obtém a estrutura da tabela
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                
                # Formata a saída
                print(f"{'Campo':<20} {'Tipo':<20} {'Nulo':<10} {'Chave':<10} {'Padrão':<20} {'Extra':<20}")
                print("-"*100)
                
                for column in columns:
                    field = column[0]
                    type_ = column[1]
                    null = column[2]
                    key = column[3]
                    default = column[4] if column[4] is not None else "NULL"
                    extra = column[5]
                    
                    print(f"{field:<20} {type_:<20} {null:<10} {key:<10} {default:<20} {extra:<20}")
                
                # Verifica se as colunas version e last_modified existem
                has_version = any(column[0] == 'version' for column in columns)
                has_last_modified = any(column[0] == 'last_modified' for column in columns)
                
                if has_version and has_last_modified:
                    print("\nA tabela possui as colunas 'version' e 'last_modified'.")
                else:
                    missing = []
                    if not has_version:
                        missing.append('version')
                    if not has_last_modified:
                        missing.append('last_modified')
                    
                    print(f"\nA tabela NÃO possui as colunas: {', '.join(missing)}")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao mostrar estrutura das tabelas no MySQL: {e}")
            raise
    
    def _show_sqlite_structure(self):
        """Mostra a estrutura detalhada das tabelas no SQLite"""
        self._run_in_thread(self._show_sqlite_structure_impl)
    
    def _show_sqlite_structure_impl(self):
        """Implementação da exibição da estrutura das tabelas no SQLite"""
        print("\n" + "="*50)
        print("ESTRUTURA DAS TABELAS NO SQLITE")
        print("="*50)
        
        try:
            # Obtém conexão com o banco SQLite
            sqlite_conn = self.db_conn.get_sqlite_connection()
            
            # Obtém a lista de tabelas
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Para cada tabela, mostra a estrutura
            for table in tables:
                print("\n" + "-"*50)
                print(f"TABELA: {table}")
                print("-"*50)
                
                # Obtém a estrutura da tabela
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # Formata a saída
                print(f"{'ID':<5} {'Campo':<20} {'Tipo':<20} {'Nulo':<10} {'Padrão':<20} {'PK':<5}")
                print("-"*80)
                
                for column in columns:
                    cid = column[0]
                    name = column[1]
                    type_ = column[2]
                    notnull = "NOT NULL" if column[3] else "NULL"
                    dflt_value = column[4] if column[4] is not None else "NULL"
                    pk = column[5]
                    
                    print(f"{cid:<5} {name:<20} {type_:<20} {notnull:<10} {dflt_value:<20} {pk:<5}")
                
                # Verifica se as colunas version e last_modified existem
                has_version = any(column[1] == 'version' for column in columns)
                has_last_modified = any(column[1] == 'last_modified' for column in columns)
                
                if has_version and has_last_modified:
                    print("\nA tabela possui as colunas 'version' e 'last_modified'.")
                else:
                    missing = []
                    if not has_version:
                        missing.append('version')
                    if not has_last_modified:
                        missing.append('last_modified')
                    
                    print(f"\nA tabela NÃO possui as colunas: {', '.join(missing)}")
                
                # Verifica se existem triggers para atualizar version e last_modified
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='trigger' AND tbl_name='{table}' 
                    AND name LIKE 'update_%_version_and_timestamp'
                """)
                trigger = cursor.fetchone()
                
                if trigger:
                    print(f"A tabela possui trigger para atualizar 'version' e 'last_modified': {trigger[0]}")
                else:
                    print("A tabela NÃO possui trigger para atualizar 'version' e 'last_modified'")
            
            # Fecha a conexão
            cursor.close()
            
        except Exception as e:
            print(f"Erro ao mostrar estrutura das tabelas no SQLite: {e}")
            raise

def main():
    """Função principal"""
    app = DatabaseSetupApp()
    app.mainloop()

if __name__ == "__main__":
    main() 
"""
Interface de usuário para gerenciamento de sincronização.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, Any
from app.data.mysql.mysql_connection import MySQLConnection
from app.config.encrypted_settings import EncryptedSettings

logger = logging.getLogger(__name__)

class SyncManagerUI(ttk.Frame):
    """Interface de usuário para gerenciamento de sincronização."""
    
    def __init__(self, parent: tk.Widget, local_settings: EncryptedSettings, remote_settings: EncryptedSettings):
        """
        Inicializa a interface de sincronização.
        
        Args:
            parent: Widget pai
            local_settings: Configurações do banco local
            remote_settings: Configurações do banco remoto
        """
        super().__init__(parent)
        
        self.local_settings = local_settings
        self.remote_settings = remote_settings
        
        # Gerenciadores
        self.mysql_connection = None
        
        # Status de conexão
        self.local_status = tk.StringVar(value="Não conectado")
        self.remote_status = tk.StringVar(value="Não conectado")
        
        # Progresso
        self.progress_var = tk.DoubleVar()
        
        self._init_ui()
        self.initialize_managers()
    
    def _init_ui(self):
        """Inicializa os elementos da interface."""
        # Frame de status
        status_frame = ttk.LabelFrame(self, text="Status de Conexão")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_frame, text="Local:").grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.local_status).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(status_frame, text="Remoto:").grid(row=1, column=0, padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.remote_status).grid(row=1, column=1, padx=5, pady=2)
        
        # Frame de ações
        actions_frame = ttk.LabelFrame(self, text="Ações")
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(actions_frame, text="Verificar Conexões", 
                  command=self.check_connections).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(actions_frame, text="Verificar Estruturas", 
                  command=self.check_structures).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(actions_frame, text="Sincronizar Local → Remoto", 
                  command=lambda: self.sync_structures(True)).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(actions_frame, text="Sincronizar Remoto → Local", 
                  command=lambda: self.sync_structures(False)).pack(fill=tk.X, padx=5, pady=2)
        
        # Barra de progresso
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, 
                                          maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
    
    def initialize_managers(self):
        """Inicializa os gerenciadores de banco de dados."""
        try:
            self.mysql_connection = MySQLConnection(self.local_settings, self.remote_settings)
            self.check_connections()
            logger.info("Gerenciadores inicializados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar gerenciadores: {e}")
            messagebox.showerror("Erro", f"Erro ao inicializar gerenciadores: {e}")
    
    def check_connections(self):
        """Verifica o status das conexões."""
        if not self.mysql_connection:
            self.local_status.set("Não inicializado")
            self.remote_status.set("Não inicializado")
            return
        
        try:
            # Testar conexão local
            self.mysql_connection.get_local_connection()
            self.local_status.set("Conectado")
        except Exception as e:
            logger.error(f"Erro na conexão local: {e}")
            self.local_status.set("Erro")
        
        try:
            # Testar conexão remota
            self.mysql_connection.get_remote_connection()
            self.remote_status.set("Conectado")
        except Exception as e:
            logger.error(f"Erro na conexão remota: {e}")
            self.remote_status.set("Erro")
    
    def check_structures(self):
        """Verifica as estruturas das tabelas."""
        if not self.mysql_connection:
            messagebox.showerror("Erro", "Conexão não inicializada")
            return
        
        try:
            # Obter lista de tabelas
            local_tables = set(self.mysql_connection.get_all_tables(is_local=True))
            remote_tables = set(self.mysql_connection.get_all_tables(is_local=False))
            
            # Comparar tabelas
            all_tables = local_tables.union(remote_tables)
            total_tables = len(all_tables)
            current_table = 0
            
            differences = []
            
            for table in all_tables:
                current_table += 1
                self.progress_var.set((current_table / total_tables) * 100)
                self.update_idletasks()
                
                if table not in local_tables:
                    differences.append(f"Tabela {table} existe apenas no banco remoto")
                    continue
                    
                if table not in remote_tables:
                    differences.append(f"Tabela {table} existe apenas no banco local")
                    continue
                
                # Comparar estruturas
                are_equal, diff = self.mysql_connection.compare_table_structures(table)
                if not are_equal:
                    differences.append(f"Tabela {table}: {diff}")
            
            # Exibir resultado
            if differences:
                messagebox.showwarning("Diferenças Encontradas", 
                                     "As seguintes diferenças foram encontradas:\n\n" + 
                                     "\n".join(differences))
            else:
                messagebox.showinfo("Verificação Concluída", 
                                  "Nenhuma diferença encontrada nas estruturas")
                
        except Exception as e:
            logger.error(f"Erro ao verificar estruturas: {e}")
            messagebox.showerror("Erro", f"Erro ao verificar estruturas: {e}")
        finally:
            self.progress_var.set(0)
    
    def sync_structures(self, source_is_local: bool):
        """
        Sincroniza as estruturas das tabelas.
        
        Args:
            source_is_local: Se True, usa estruturas locais como fonte
        """
        if not self.mysql_connection:
            messagebox.showerror("Erro", "Conexão não inicializada")
            return
        
        try:
            # Confirmar ação
            source = "local" if source_is_local else "remoto"
            dest = "remoto" if source_is_local else "local"
            
            if not messagebox.askyesno("Confirmar Sincronização",
                                     f"Isso irá sincronizar as estruturas do banco {source} para o {dest}.\n\n" +
                                     "Deseja continuar?"):
                return
            
            # Executar sincronização
            report = self.mysql_connection.check_and_sync_structures(source_is_local)
            
            # Exibir resultado
            if report['success']:
                messagebox.showinfo("Sincronização Concluída",
                                  f"Sincronização concluída com sucesso.\n\n" +
                                  f"Tabelas sincronizadas: {len(report['synced_tables'])}")
            else:
                messagebox.showwarning("Sincronização Parcial",
                                     f"A sincronização foi concluída com alguns erros:\n\n" +
                                     f"Tabelas sincronizadas: {len(report['synced_tables'])}\n" +
                                     f"Tabelas com erro: {len(report['failed_tables'])}\n\n" +
                                     "Erros:\n" + "\n".join(report['errors']))
                
        except Exception as e:
            logger.error(f"Erro ao sincronizar estruturas: {e}")
            messagebox.showerror("Erro", f"Erro ao sincronizar estruturas: {e}")
        finally:
            self.progress_var.set(0) 
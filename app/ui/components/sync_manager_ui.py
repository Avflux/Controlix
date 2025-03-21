import customtkinter as ctk
import logging
import threading
import time
from typing import Optional, Callable, Dict, List
from pathlib import Path
import mysql.connector
from datetime import datetime
import json

from app.data.mysql.sync_manager import MySQLSyncManager, TableConfig, ConflictResolutionStrategy
from app.data.migrations.manager import MigrationManager
from app.config.settings import DATABASE
from app.ui.notifications import notifications
from app.ui.dialogs.conflict_resolution_dialog import ConflictResolutionDialog
from app.data.connection import get_db_connection
from app.config.logging_config import get_logger

logger = get_logger('app')

class SyncManagerUI(ctk.CTkFrame):
    """Interface de usuário para gerenciamento de sincronização entre MySQL local e remoto"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.sync_manager: Optional[MySQLSyncManager] = None
        self.migration_manager: Optional[MigrationManager] = None
        self.sync_thread: Optional[threading.Thread] = None
        self.is_syncing = False
        self.auto_sync_enabled = False
        self.auto_sync_interval = 30  # minutos
        self.db_connection = get_db_connection()
        
        # Configuração do layout
        self.grid_columnconfigure(0, weight=1)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self, 
            text="Gerenciador de Sincronização",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Status da conexão
        self.connection_frame = ctk.CTkFrame(self)
        self.connection_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.connection_frame.grid_columnconfigure(1, weight=1)
        
        self.local_status_label = ctk.CTkLabel(
            self.connection_frame, 
            text="MySQL Local:",
            font=ctk.CTkFont(weight="bold")
        )
        self.local_status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.local_status_value = ctk.CTkLabel(
            self.connection_frame, 
            text="Desconectado",
            text_color="red"
        )
        self.local_status_value.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.remote_status_label = ctk.CTkLabel(
            self.connection_frame, 
            text="MySQL Remoto:",
            font=ctk.CTkFont(weight="bold")
        )
        self.remote_status_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.remote_status_value = ctk.CTkLabel(
            self.connection_frame, 
            text="Desconectado",
            text_color="red"
        )
        self.remote_status_value.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Última sincronização
        self.last_sync_label = ctk.CTkLabel(
            self.connection_frame, 
            text="Última sincronização:",
            font=ctk.CTkFont(weight="bold")
        )
        self.last_sync_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.last_sync_value = ctk.CTkLabel(
            self.connection_frame, 
            text="Nunca"
        )
        self.last_sync_value.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Botões de ação
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.sync_button = ctk.CTkButton(
            self.button_frame,
            text="Sincronizar Agora",
            command=self.start_sync
        )
        self.sync_button.pack(side="left", padx=10, pady=10)
        
        self.auto_sync_var = ctk.BooleanVar(value=False)
        self.auto_sync_checkbox = ctk.CTkCheckBox(
            self.button_frame,
            text="Sincronização Automática",
            variable=self.auto_sync_var,
            command=self.toggle_auto_sync
        )
        self.auto_sync_checkbox.pack(side="left", padx=10, pady=10)
        
        # Progresso
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Progresso:"
        )
        self.progress_label.pack(side="top", anchor="w", padx=10, pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="top", fill="x", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Pronto"
        )
        self.status_label.pack(side="top", anchor="w", padx=10, pady=(0, 10))
        
        # Estatísticas
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        self.stats_frame.grid_columnconfigure(1, weight=1)
        
        stats_title = ctk.CTkLabel(
            self.stats_frame,
            text="Estatísticas de Sincronização",
            font=ctk.CTkFont(weight="bold")
        )
        stats_title.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.records_synced_label = ctk.CTkLabel(
            self.stats_frame,
            text="Registros sincronizados:"
        )
        self.records_synced_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.records_synced_value = ctk.CTkLabel(
            self.stats_frame,
            text="0"
        )
        self.records_synced_value.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        self.conflicts_label = ctk.CTkLabel(
            self.stats_frame,
            text="Conflitos detectados:"
        )
        self.conflicts_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.conflicts_value = ctk.CTkLabel(
            self.stats_frame,
            text="0"
        )
        self.conflicts_value.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Botão para resolver conflitos
        self.resolve_conflicts_button = ctk.CTkButton(
            self.stats_frame,
            text="Resolver Conflitos",
            command=self.show_conflict_resolution,
            state="disabled"
        )
        self.resolve_conflicts_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Inicializa os gerenciadores
        self.initialize_managers()
        
        # Verifica status inicial
        self.check_connection_status()
    
    def initialize_managers(self):
        """Inicializa os gerenciadores de sincronização e migração"""
        try:
            # Inicializa gerenciador de migração
            self.migration_manager = MigrationManager()
            
            # O MySQLSyncManager será inicializado durante a sincronização
            # com as conexões ativas
            
            logger.info("Gerenciadores de sincronização e migração inicializados")
        except Exception as e:
            logger.error(f"Erro ao inicializar gerenciadores: {e}", exc_info=True)
            notifications.show_error("Erro ao inicializar sincronização", str(e))
    
    def check_connection_status(self):
        """Verifica o status das conexões com os bancos de dados"""
        # Verifica MySQL Local
        local_connected = False
        remote_connected = False
        
        try:
            # Tenta obter uma conexão MySQL local
            conn = self.db_connection.get_connection(is_local=True)
            if conn:
                local_connected = True
                self.db_connection.release_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao verificar conexão MySQL local: {e}", exc_info=True)
            local_connected = False
            
        try:
            # Tenta obter uma conexão MySQL remota
            conn = self.db_connection.get_connection(is_local=False)
            if conn:
                remote_connected = True
                self.db_connection.release_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao verificar conexão MySQL remota: {e}", exc_info=True)
            remote_connected = False
        
        # Atualiza interface
        if local_connected:
            self.local_status_value.configure(text="Conectado", text_color="green")
        else:
            self.local_status_value.configure(text="Desconectado", text_color="red")
            
        if remote_connected:
            self.remote_status_value.configure(text="Conectado", text_color="green")
        else:
            self.remote_status_value.configure(text="Desconectado", text_color="red")
        
        # Atualiza última sincronização
        try:
            # Tenta obter a última sincronização do banco MySQL
            result = self.db_connection.execute_query(
                "SELECT value FROM sync_metadata WHERE key_name='last_sync'", 
                is_local=True
            )
            
            if result and result[0]['value']:
                # Converte ISO format para datetime
                last_sync = datetime.fromisoformat(result[0]['value']).strftime("%d/%m/%Y %H:%M:%S")
                self.last_sync_value.configure(text=last_sync)
            else:
                # Tenta na tabela sync_log
                result = self.db_connection.execute_query(
                    "SELECT MAX(created_at) as last_sync FROM sync_log",
                    is_local=True
                )
                
                if result and result[0]['last_sync']:
                    last_sync = result[0]['last_sync'].strftime("%d/%m/%Y %H:%M:%S")
                    self.last_sync_value.configure(text=last_sync)
                else:
                    self.last_sync_value.configure(text="Nunca")
                
        except Exception as e:
            logger.error(f"Erro ao verificar última sincronização: {e}", exc_info=True)
            self.last_sync_value.configure(text="Erro ao verificar")
        
        # Verifica conflitos pendentes
        try:
            # Verifica se há conflitos pendentes
            result = self.db_connection.execute_query(
                "SELECT COUNT(*) as count FROM sync_conflicts WHERE resolved_at IS NULL",
                is_local=True
            )
            
            if result and result[0]['count'] > 0:
                    self.resolve_conflicts_button.configure(state="normal")
            else:
                self.resolve_conflicts_button.configure(state="disabled")
                
        except Exception as e:
            logger.error(f"Erro ao verificar conflitos pendentes: {e}", exc_info=True)
            self.resolve_conflicts_button.configure(state="disabled")
        
        # Agenda próxima verificação
        self.after(60000, self.check_connection_status)  # Verifica a cada minuto
    
    def start_sync(self):
        """Inicia o processo de sincronização em uma thread separada"""
        if self.is_syncing:
            notifications.show_warning("Sincronização em andamento", "Aguarde a conclusão da sincronização atual.")
            return
        
        self.is_syncing = True
        self.sync_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Iniciando sincronização...")
        
        # Inicia thread de sincronização
        self.sync_thread = threading.Thread(target=self._sync_thread_func)
        self.sync_thread.daemon = True
        self.sync_thread.start()
    
    def _sync_thread_func(self):
        """Função executada pela thread de sincronização"""
        try:
            # Atualiza interface
            self._update_ui("Verificando conexões...", 0.1)
            
            # Verifica conexão com MySQL local e remoto
            local_connected = False
            remote_connected = False
            
            try:
                # Tenta obter uma conexão MySQL local
                local_conn = self.db_connection.get_connection(is_local=True)
                if local_conn:
                    local_connected = True
                    self.db_connection.release_connection(local_conn)
            except Exception as e:
                logger.error(f"Erro ao verificar conexão MySQL local: {e}", exc_info=True)
                local_connected = False
                
            try:
                # Tenta obter uma conexão MySQL remota
                remote_conn = self.db_connection.get_connection(is_local=False)
                if remote_conn:
                    remote_connected = True
                    self.db_connection.release_connection(remote_conn)
            except Exception as e:
                logger.error(f"Erro ao verificar conexão MySQL remota: {e}", exc_info=True)
                remote_connected = False
            
            if not local_connected:
                self._update_ui("MySQL local não disponível. Sincronização cancelada.", 0)
                notifications.show_warning(
                    "Sincronização não realizada", 
                    "Não foi possível conectar ao banco MySQL local. Verifique sua conexão."
                )
                self.is_syncing = False
                self.sync_button.configure(state="normal")
                return
                
            if not remote_connected:
                self._update_ui("MySQL remoto não disponível. Sincronização cancelada.", 0)
                notifications.show_warning(
                    "Sincronização não realizada", 
                    "Não foi possível conectar ao banco MySQL remoto. Verifique sua conexão."
                )
                self.is_syncing = False
                self.sync_button.configure(state="normal")
                return
            
            # Inicializa o gerenciador de sincronização
            self._update_ui("Inicializando sincronização...", 0.2)
            
            # Verifica schema
            try:
                # Verifica se as tabelas necessárias existem
                result = self.db_connection.execute_query(
                    "SHOW TABLES LIKE 'sync_metadata'",
                    is_local=True
                )
                
                if not result:
                    logger.warning("Tabela sync_metadata não encontrada. Use database_setup_ui.py para criar tabelas.")
                    self._update_ui("Tabelas de sincronização não encontradas. Use a interface de configuração do banco de dados.", 0)
                    notifications.show_warning(
                        "Sincronização não realizada", 
                        "As tabelas necessárias para sincronização não foram encontradas.\n\n"
                        "Use a interface de configuração do banco de dados para criar as tabelas necessárias."
                    )
                    self.is_syncing = False
                    self.sync_button.configure(state="normal")
                    return False
                
                # Verifica e atualiza o schema MySQL se necessário
                self.migration_manager.verify_schema()
                self.migration_manager.migrate()
                
            except Exception as e:
                logger.error(f"Erro ao verificar schema: {e}", exc_info=True)
                self._update_ui(f"Erro ao verificar schema: {str(e)}", 0)
                notifications.show_error("Erro de sincronização", f"Falha ao verificar schema: {str(e)}")
                self.is_syncing = False
                self.sync_button.configure(state="normal")
                return
            
            # Inicializa o gerenciador de sincronização
            self._update_ui("Iniciando sincronização...", 0.3)
            
            # Cria instância do gerenciador de sincronização
            self.sync_manager = MySQLSyncManager()
            
            # Executa sincronização
            self._update_ui("Sincronizando dados...", 0.4)
            
            # Executa sincronização
            sync_stats = self.sync_manager.synchronize()
                
                # Atualiza estatísticas
            records_synced = sync_stats.get('records_synced', 0)
            conflicts = sync_stats.get('conflicts', 0)
            
            # Atualiza interface
            self._update_ui("Sincronização concluída com sucesso", 1.0)
            self._update_stats(records_synced, conflicts)
            
            # Atualiza última sincronização
            self.check_connection_status()
            
            # Notifica o usuário
            if conflicts > 0:
                notifications.show_warning(
                    "Sincronização concluída com conflitos", 
                    f"Sincronização concluída com {conflicts} conflitos. Clique em 'Resolver Conflitos' para resolvê-los."
                )
            else:
                notifications.show_success(
                    "Sincronização concluída", 
                    f"Sincronização concluída com sucesso. {records_synced} registros sincronizados."
                )
            
        except Exception as e:
            logger.error(f"Erro durante sincronização: {e}", exc_info=True)
            self._update_ui(f"Erro durante sincronização: {str(e)}", 0)
            notifications.show_error("Erro de sincronização", str(e))
        finally:
            # Restaura estado da interface
            self.is_syncing = False
            self.sync_button.configure(state="normal")
    
    def _update_ui(self, status_text, progress_value):
        """Atualiza a interface com o progresso da sincronização"""
        # Como estamos em uma thread, usamos after para atualizar a UI na thread principal
        self.after(0, lambda: self.status_label.configure(text=status_text))
        self.after(0, lambda: self.progress_bar.set(progress_value))
    
    def _update_stats(self, records_synced, conflicts):
        """Atualiza as estatísticas de sincronização"""
        self.after(0, lambda: self.records_synced_value.configure(text=str(records_synced)))
        self.after(0, lambda: self.conflicts_value.configure(text=str(conflicts)))
    
    def toggle_auto_sync(self):
        """Ativa ou desativa a sincronização automática"""
        self.auto_sync_enabled = self.auto_sync_var.get()
        
        if self.auto_sync_enabled:
            notifications.show_info(
                "Sincronização automática ativada", 
                f"Os dados serão sincronizados a cada {self.auto_sync_interval} minutos."
            )
            self._schedule_auto_sync()
        else:
            notifications.show_info(
                "Sincronização automática desativada", 
                "A sincronização será realizada apenas manualmente."
            )
    
    def _schedule_auto_sync(self):
        """Agenda a próxima sincronização automática"""
        if not self.auto_sync_enabled:
            return
        
        # Agenda próxima sincronização
        self.after(self.auto_sync_interval * 60 * 1000, self._auto_sync)
    
    def _auto_sync(self):
        """Executa sincronização automática"""
        if not self.auto_sync_enabled:
            return
        
        logger.info("Iniciando sincronização automática")
        self.start_sync()
        
        # Agenda próxima sincronização
        self._schedule_auto_sync()
    
    def show_conflict_resolution(self):
        """Mostra o diálogo de resolução de conflitos"""
        try:
            # Obtém conflitos pendentes
            conflicts = self.db_connection.execute_query(
                "SELECT * FROM sync_conflicts WHERE resolved_at IS NULL",
                is_local=True
            )
            
            if not conflicts:
                notifications.show_info(
                    "Sem conflitos", 
                    "Não há conflitos pendentes para resolução."
                )
                return
            
            # Processa conflitos para o formato esperado pelo diálogo
            self.processed_conflicts = []
            
            for conflict in conflicts:
                # Converte dados JSON para dicionários
                local_data = json.loads(conflict.get('local_data', '{}'))
                remote_data = json.loads(conflict.get('remote_data', '{}'))
                
                # Cria objeto de conflito
                processed_conflict = {
                    'id': conflict.get('id'),
                    'table': conflict.get('table_name'),
                    'record_id': conflict.get('record_id'),
                    'local_data': local_data,
                    'remote_data': remote_data,
                    'local_version': conflict.get('local_version', 1),
                    'remote_version': conflict.get('remote_version', 1),
                    'local_modified': conflict.get('local_modified', ''),
                    'remote_modified': conflict.get('remote_modified', ''),
                    'created_at': conflict.get('created_at', '')
                }
                
                self.processed_conflicts.append(processed_conflict)
            
            # Inicializa o índice do conflito atual
            self.current_conflict_index = 0
            
            # Mostra o primeiro conflito
            if self.processed_conflicts:
                self.current_conflict = self.processed_conflicts[0]
                dialog = ConflictResolutionDialog(
                    self, 
                    self.current_conflict, 
                    self._resolve_conflict
                )
                
                # Aguarda o diálogo ser fechado antes de continuar
                self.wait_window(dialog)
            
        except Exception as e:
            logger.error(f"Erro ao mostrar diálogo de resolução de conflitos: {e}", exc_info=True)
            notifications.show_error("Erro", f"Não foi possível mostrar o diálogo de resolução de conflitos: {e}")
    
    def _resolve_conflict(self, resolved_data: Dict, resolution_type: str):
        """
        Resolve um conflito com os dados fornecidos.
        
        Args:
            resolved_data: Dados resolvidos
            resolution_type: Tipo de resolução (local, remote, newest, manual)
        """
        try:
            # Obtém o conflito atual
            conflict_id = self.current_conflict['id']
            table_name = self.current_conflict['table']
            record_id = self.current_conflict['record_id']
            
            # Incrementa a versão
            if 'version' in resolved_data:
                resolved_data['version'] = resolved_data['version'] + 1
            
            # Atualiza o registro no banco local
            columns = ', '.join([f"{key} = %s" for key in resolved_data.keys()])
            values = list(resolved_data.values())
            values.append(record_id)
            
            self.db_connection.execute_update(
                f"UPDATE {table_name} SET {columns} WHERE id = %s",
                tuple(values),
                is_local=True
            )
            
            # Atualiza o registro no banco remoto se disponível
            try:
                self.db_connection.execute_update(
                    f"UPDATE {table_name} SET {columns} WHERE id = %s",
                    tuple(values),
                    is_local=False
                )
            except Exception as e:
                logger.warning(f"Não foi possível atualizar o banco remoto: {e}")
                # Será atualizado na próxima sincronização
            
            # Marca o conflito como resolvido
            self.db_connection.execute_update(
                "UPDATE sync_conflicts SET resolved_at = NOW(), resolution_type = %s, resolved_data = %s WHERE id = %s",
                (resolution_type, json.dumps(resolved_data), conflict_id),
                is_local=True
            )
            
            # Notifica o usuário
            notifications.show_success(
                "Conflito resolvido", 
                f"Conflito na tabela {table_name} (ID: {record_id}) foi resolvido com sucesso."
            )
            
            # Atualiza a lista de conflitos
            self.current_conflict_index += 1
            if self.current_conflict_index < len(self.processed_conflicts):
                self.current_conflict = self.processed_conflicts[self.current_conflict_index]
                # Mostra o próximo conflito
                dialog = ConflictResolutionDialog(
                    self, 
                    self.current_conflict, 
                    self._resolve_conflict
                )
            else:
                # Todos os conflitos foram resolvidos
                notifications.show_success(
                    "Todos os conflitos resolvidos", 
                    "Todos os conflitos foram resolvidos com sucesso."
            )
            
        except Exception as e:
            logger.error(f"Erro ao resolver conflito: {e}", exc_info=True)
            notifications.show_error("Erro", f"Não foi possível resolver o conflito: {e}") 
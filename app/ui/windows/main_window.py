import logging
import customtkinter as ctk
from typing import Optional
from app.config.settings import APP_NAME, APP_ICONS, THEME_STYLES
from app.ui.theme.theme_manager import theme_manager
from app.ui.notifications import notifications
from app.core.scripts.window_position_mixin import WindowPositionMixin
from app.ui.components.user_config import UserConfig
from app.ui.components.sync_manager_ui import SyncManagerUI

logger = logging.getLogger(__name__)

class MainWindow(WindowPositionMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configuração da janela
        self.title(APP_NAME)
        self.geometry("1024x768")
        self.minsize(800, 600)
        
        # Configura o grid do frame principal
        self.main_frame.grid_columnconfigure(1, weight=1)  # Coluna principal se expande
        self.main_frame.grid_rowconfigure(0, weight=1)     # Linha principal se expande
        
        # Configura gerenciamento de posição
        self.setup_window_position('main_window')
        
        # Configura o ícone
        if APP_ICONS.get('main'):
            self.iconbitmap(APP_ICONS['main'])
        
        # Inicializa componentes
        self._create_sidebar()
        self._create_content_area()
        self._create_status_bar()
        
        # Registra para atualizações de tema
        theme_manager.add_observer(self._on_theme_change)
        
        logger.debug("Janela principal inicializada")
    
    def _create_sidebar(self):
        """Cria a barra lateral com menu"""
        self.sidebar = ctk.CTkFrame(
            self.main_frame,
            fg_color=THEME_STYLES[theme_manager.current_theme]['sidebar']
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Logo ou título no topo
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FF8C00"
        )
        self.logo_label.pack(pady=20, padx=10)
        
        # Botões do menu
        self.menu_buttons = []
        menu_items = [
            ("📊 Dashboard", self._show_dashboard),
            ("👥 Usuários", self._show_users),
            ("🔄 Sincronização", self._show_sync_manager),
            ("⚙️ Configurações", self._show_user_config),
            ("❓ Ajuda", self._show_help)
        ]
        
        for text, command in menu_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                anchor="w",
                fg_color="transparent",
                text_color=THEME_STYLES[theme_manager.current_theme]['text_color'][0]
            )
            btn.pack(pady=5, padx=10, fill="x")
            self.menu_buttons.append(btn)
    
    def _create_content_area(self):
        """Cria a área principal de conteúdo"""
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Configura grid do content_frame
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Frame inicial (dashboard)
        self._show_dashboard()
    
    def _create_status_bar(self):
        """Cria a barra de status"""
        self.status_bar = ctk.CTkFrame(
            self.main_frame,
            height=25,
            fg_color=THEME_STYLES[theme_manager.current_theme]['frame_low'][0]
        )
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Pronto",
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=10)
        
        # Indicador de sincronização
        self.sync_status_label = ctk.CTkLabel(
            self.status_bar,
            text="MySQL: Desconectado",
            text_color="red"
        )
        self.sync_status_label.pack(side="right", padx=10)
    
    def _show_dashboard(self):
        """Mostra o dashboard"""
        self._clear_content()
        dashboard = ctk.CTkLabel(
            self.content_frame,
            text="Dashboard - Em desenvolvimento",
            font=ctk.CTkFont(size=16)
        )
        dashboard.grid(row=0, column=0, pady=20)
    
    def _show_users(self):
        """Mostra a gestão de usuários"""
        self._clear_content()
        users = ctk.CTkLabel(
            self.content_frame,
            text="Gestão de Usuários - Em desenvolvimento",
            font=ctk.CTkFont(size=16)
        )
        users.grid(row=0, column=0, pady=20)
    
    def _show_sync_manager(self):
        """Mostra o gerenciador de sincronização"""
        self._clear_content()
        
        # Configura o grid para o conteúdo
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Cria o componente de sincronização
        sync_manager = SyncManagerUI(self.content_frame)
        sync_manager.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Atualiza o status na barra de status
        self.update_sync_status()
    
    def update_sync_status(self):
        """Atualiza o status de sincronização na barra de status"""
        # Em uma implementação real, verificaria o status real da conexão
        # Por enquanto, apenas simula o status
        mysql_connected = False  # Simulado
        
        if mysql_connected:
            self.sync_status_label.configure(text="MySQL: Conectado", text_color="green")
        else:
            self.sync_status_label.configure(text="MySQL: Desconectado", text_color="red")
    
    def _show_user_config(self):
        """Mostra a interface de configurações do usuário."""
        self._clear_content()
        user_config = UserConfig(self.content_frame)
        user_config.pack(fill="both", expand=True)
    
    def _show_help(self):
        """Mostra a ajuda"""
        self._clear_content()
        help_text = ctk.CTkLabel(
            self.content_frame,
            text="Ajuda - Em desenvolvimento",
            font=ctk.CTkFont(size=16)
        )
        help_text.grid(row=0, column=0, pady=20)
    
    def _clear_content(self):
        """Limpa a área de conteúdo"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _on_theme_change(self):
        """Atualiza cores quando o tema muda"""
        current_colors = THEME_STYLES[theme_manager.current_theme]
        
        # Atualiza cores da sidebar
        self.sidebar.configure(fg_color=current_colors['sidebar'])
        
        # Atualiza cores dos botões do menu
        for btn in self.menu_buttons:
            btn.configure(text_color=current_colors['text_color'][0])
        
        # Atualiza status bar
        self.status_bar.configure(fg_color=current_colors['frame_low'][0]) 
import logging
import customtkinter as ctk
from typing import Optional, Callable, Dict
from app.data.connection import db
from app.config.settings import LOGIN_WINDOW_SETTINGS, APP_ICONS, APP_NAME
from app.ui.theme.theme_manager import theme_manager
from app.ui.notifications import notifications
from app.core.scripts.window_position_mixin import WindowPositionMixin
from app.ui.windows.main_window import MainWindow
from app.core.observer.auth_observer import auth_observer

logger = logging.getLogger(__name__)

class LoginWindow(WindowPositionMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Frame principal para conter os widgets
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configuração inicial da janela
        self.title(APP_NAME)
        self.geometry(f"{LOGIN_WINDOW_SETTINGS['size']['width']}x{LOGIN_WINDOW_SETTINGS['size']['height']}")
        self.minsize(
            LOGIN_WINDOW_SETTINGS['size']['min_width'],
            LOGIN_WINDOW_SETTINGS['size']['min_height']
        )
        
        # Configura o grid do frame principal para ser responsivo
        self.main_frame.grid_columnconfigure(0, weight=1)  # Coluna se expande
        self.main_frame.grid_rowconfigure(1, weight=1)     # Linha do frame de login se expande
        
        # Configura gerenciamento de posição
        self.setup_window_position('login_window')
        
        # Configura o ícone da janela
        if APP_ICONS.get('main'):
            self.iconbitmap(APP_ICONS['main'])
        
        # Inicializa o tema
        theme_manager.initialize()
        
        # Cria os widgets
        self._create_widgets()
        
        # Registra para atualizações de tema
        theme_manager.add_observer(self._on_theme_change)
        
        # Registra para observar autenticação
        auth_observer.add_observer(self._on_auth_change)
        
        logger.debug("Janela de login inicializada")

    def _create_widgets(self):
        """Cria todos os widgets da janela"""
        # Título em laranja
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text=APP_NAME,
            font=ctk.CTkFont(
                size=LOGIN_WINDOW_SETTINGS['style']['title']['font_size'],
                weight=LOGIN_WINDOW_SETTINGS['style']['title']['font_weight']
            ),
            text_color="#FF8C00"  # Laranja
        )
        self.title_label.grid(row=0, column=0, pady=20, sticky="ew")
        
        # Frame para campos de login
        self.login_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )
        self.login_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        
        # Configura o grid do login_frame
        self.login_frame.grid_columnconfigure(0, weight=1)
        
        # Campo de usuário
        self.username_entry = ctk.CTkEntry(
            self.login_frame,
            placeholder_text="Usuário",
            height=LOGIN_WINDOW_SETTINGS['style']['entry']['height'],
            corner_radius=LOGIN_WINDOW_SETTINGS['style']['entry']['corner_radius'],
            border_width=LOGIN_WINDOW_SETTINGS['style']['entry']['border_width']
        )
        self.username_entry.grid(row=0, column=0, pady=10, sticky="ew")
        
        # Campo de senha
        self.password_entry = ctk.CTkEntry(
            self.login_frame,
            placeholder_text="Senha",
            show="•",
            height=LOGIN_WINDOW_SETTINGS['style']['entry']['height'],
            corner_radius=LOGIN_WINDOW_SETTINGS['style']['entry']['corner_radius'],
            border_width=LOGIN_WINDOW_SETTINGS['style']['entry']['border_width']
        )
        self.password_entry.grid(row=1, column=0, pady=10, sticky="ew")
        
        # Frame para botões
        self.button_frame = ctk.CTkFrame(
            self.login_frame,
            fg_color="transparent"
        )
        self.button_frame.grid(row=2, column=0, pady=20, sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=1)
        
        # Botões (já pegarão a cor do tema)
        self.login_button = ctk.CTkButton(
            self.button_frame,
            text="Conectar",
            command=self._handle_login
        )
        self.login_button.grid(row=0, column=0, pady=5, sticky="ew")
        
        # Status label no final
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            text_color="gray"
        )
        self.status_label.grid(row=2, column=0, pady=10, sticky="ew")
        
        # Registra o label de status no gerenciador de conexão
        db.set_status_label(self.status_label)

    def _handle_login(self):
        """Gerencia o processo de login"""
        try:
            self.login_button.configure(state="disabled")
            self.status_label.configure(text="Conectando...", text_color="gray")
            
            credentials = {
                'user': self.username_entry.get(),
                'password': self.password_entry.get()
            }
            
            if db.test_connection(credentials):
                # A notificação será feita pelo observer
                self.withdraw()  # Esconde a janela de login
                main_window = MainWindow()
                main_window.protocol("WM_DELETE_WINDOW", self._on_main_window_close)
                main_window.mainloop()
            else:
                self.status_label.configure(
                    text="Usuário ou senha inválidos",
                    text_color="red"
                )
                
        except Exception as e:
            logger.error(f"Erro ao tentar login: {e}")
            self.status_label.configure(
                text=f"Erro: {str(e)}",
                text_color="red"
            )
        finally:
            self.login_button.configure(state="normal")

    def _on_main_window_close(self):
        """Chamado quando a janela principal é fechada"""
        self.quit()  # Fecha a aplicação

    def _on_theme_change(self):
        """Callback para mudanças de tema"""
        # Aqui você pode adicionar lógica específica para quando o tema mudar
        pass

    def _on_auth_change(self, status: bool, user_data: Optional[Dict]):
        """Callback para mudanças no status de autenticação"""
        if status:
            notifications.notify(
                "Login Realizado",
                f"Bem-vindo, {user_data['name_id']}!",
                "success"
            )
        else:
            self.deiconify()  # Mostra a janela de login novamente
            self.status_label.configure(text="Sessão encerrada", text_color="gray")

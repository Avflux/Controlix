import customtkinter as ctk
from app.ui.theme.theme_manager import theme_manager
from app.config.settings import NOTIFICATIONS, THEME_STYLES, dynamic_settings
from app.ui.notifications import notifications
import logging
import time

logger = logging.getLogger(__name__)

class UserConfig(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.configure(fg_color="transparent")
        
        # Título da seção de configurações
        self.title_label = ctk.CTkLabel(self, text="Configurações do Usuário", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        # Título da seção de tema
        self.theme_title = ctk.CTkLabel(self, text="Tema", font=ctk.CTkFont(size=16, weight="bold"))
        self.theme_title.pack(anchor="w", padx=10, pady=(20, 10))

        # Frame para o label e o switch de tema
        self.theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.theme_frame.pack(anchor="w", padx=10, pady=10)

        # Label para o switch de tema
        self.theme_label = ctk.CTkLabel(self.theme_frame, text="Claro/Escuro", font=ctk.CTkFont(size=14))
        self.theme_label.pack(side="left", padx=(5, 0))

        # Switch para alternar tema
        self.theme_switch = ctk.CTkSwitch(
            self.theme_frame,
            text="",  # Remove o texto CTkSwitch
            command=self.toggle_theme,
            button_color="#FF8C00",  # Cor laranja quando ativado
            button_hover_color="#E67E00",  # Cor laranja mais escura para hover
            progress_color="#FF8C00"  # Cor da barra de progresso quando ativado
        )
        self.theme_switch.pack(side="left", padx=(10, 0))

        # Título da seção de notificações
        self.notifications_title = ctk.CTkLabel(self, text="Notificações", font=ctk.CTkFont(size=16, weight="bold"))
        self.notifications_title.pack(anchor="w", padx=10, pady=(20, 10))

        # Dicionário de notificações com seus respectivos títulos
        notifications_config = {
            'start': "Início do Expediente",
            'interval_start': "Hora do Almoço",
            'interval_end': "Retorno do Almoço",
            'end': "Fim do Expediente",
            'coffee': "Hora do Café",
            'water': "Hidratação"
        }

        # Criando frames individuais para cada notificação
        self.notification_vars = {}
        for key, title in notifications_config.items():
            # Frame para cada notificação
            notification_frame = ctk.CTkFrame(self, fg_color="transparent")
            notification_frame.pack(anchor="w", padx=10, pady=5)

            # Label da notificação
            label = ctk.CTkLabel(notification_frame, text=title, font=ctk.CTkFont(size=14))
            label.pack(side="left")

            # Variável de controle para o switch
            self.notification_vars[key] = ctk.BooleanVar(
                value=NOTIFICATIONS['tray']['business_notifications'][key]['enabled']
            )
            self.notification_vars[key].trace_add('write', lambda *args, k=key: self._on_notification_toggle(k))

            # Switch sem texto e com cores personalizadas
            switch = ctk.CTkSwitch(
                notification_frame, 
                text="",
                variable=self.notification_vars[key],
                width=40,
                button_color="#FF8C00",
                button_hover_color="#E67E00",
                progress_color="#FF8C00"
            )
            switch.pack(side="left", padx=(10, 0))

        # Registrar para atualizações de configuração
        dynamic_settings.add_observer(self._on_settings_changed)

        self.last_toggle_time = 0  # Para controle de debounce

    def toggle_theme(self):
        """Alterna entre tema claro e escuro."""
        theme_manager.toggle_theme()

    def _on_settings_changed(self, setting_type: str = None):
        """Callback para mudanças nas configurações"""
        if setting_type == 'notifications':
            self._update_notification_switches()

    def _update_notification_switches(self):
        """Atualiza o estado dos switches baseado nas configurações"""
        for key, var in self.notification_vars.items():
            enabled = dynamic_settings.get_notification_setting(
                ['tray', 'business_notifications', key, 'enabled'],
                default=True
            )
            var.set(enabled)

    def _on_notification_toggle(self, notification_key: str):
        """Callback para quando uma notificação é alternada."""
        current_time = time.time()
        if current_time - self.last_toggle_time < 0.5:  # 500ms debounce
            return  # Ignora se a chamada for muito rápida

        self.last_toggle_time = current_time  # Atualiza o tempo do último toggle

        try:
            is_enabled = self.notification_vars[notification_key].get()
            status = 'ativada' if is_enabled else 'desativada'
            
            # Atualiza as configurações
            dynamic_settings.set_notification_setting(
                ['tray', 'business_notifications', notification_key, 'enabled'],
                is_enabled
            )
            
            # Atualiza o gerenciador de notificações
            if hasattr(notifications, 'business_hours'):
                notifications.business_hours.update_notification_state(notification_key, is_enabled)
            
            # Log no console e arquivo
            logger.info(f"Notificação '{notification_key}' foi {status}")
            
        except Exception as e:
            error_msg = f"Erro ao alternar notificação {notification_key}: {e}"
            logger.error(error_msg)
            notifications.notify(
                title="Erro na Configuração",
                message=error_msg,
                level="error",
                timeout=5
            )

import logging
import customtkinter as ctk
from app.config.settings import ThemeMode, THEME_STYLES, APP_NAME, dynamic_settings
import json
from pathlib import Path
from typing import Callable, List

logger = logging.getLogger(__name__)

class ThemeManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            logger.debug("Criando nova instância do ThemeManager")
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.debug("Iniciando ThemeManager...")
        self._observers: List[Callable] = []
        
        # Usa o dynamic_settings ao invés de ler diretamente do arquivo
        self._theme_mode = ThemeMode(dynamic_settings.get_window_setting('appearance_mode', 'system'))
        
        # Aplica o tema inicial
        self._apply_theme()
        
        # Registra-se como observador das configurações
        dynamic_settings.add_observer(self._on_settings_changed)
        
        self._initialized = True
        logger.debug(f"ThemeManager inicializado com sucesso. Tema atual: {self.current_theme.value}")
    
    def add_observer(self, callback: Callable) -> None:
        """Adiciona um observador para mudanças de tema"""
        if callback not in self._observers:
            self._observers.append(callback)
            logger.debug(f"Observador adicionado: {callback.__name__}")
    
    def remove_observer(self, callback: Callable) -> None:
        """Remove um observador"""
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug(f"Observador removido: {callback.__name__}")
    
    def _notify_observers(self) -> None:
        """Notifica todos os observadores sobre mudança de tema"""
        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                logger.error(f"Erro ao notificar observador {callback.__name__}: {e}")

    def initialize(self):
        """Inicializa o tema após CTk estar disponível"""
        logger.debug("Inicializando tema...")
        self._apply_theme()
        logger.debug("Tema aplicado com sucesso")

    @property
    def current_theme(self) -> ThemeMode:
        """Retorna o tema atual"""
        return self._theme_mode
    
    def _on_settings_changed(self, setting_type: str = None):
        """Callback para mudanças nas configurações"""
        if setting_type in (None, 'window', 'appearance_mode'):
            new_mode = dynamic_settings.get_window_setting('appearance_mode', 'system')
            if new_mode != self.current_theme.value:
                self._theme_mode = ThemeMode(new_mode)
                self._apply_theme()
    
    def set_theme(self, theme: ThemeMode) -> bool:
        """Define um novo tema"""
        try:
            self._theme_mode = theme
            # Atualiza as configurações através do dynamic_settings
            dynamic_settings.set_window_setting('appearance_mode', theme.value)
            self._apply_theme()
            self._notify_observers()
            
            logger.info(f"Tema alterado para: {theme.value}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao alterar tema: {e}")
            return False
    
    def toggle_theme(self) -> bool:
        """Alterna entre tema claro e escuro"""
        current = self.current_theme
        if current == ThemeMode.LIGHT:
            return self.set_theme(ThemeMode.DARK)
        else:
            return self.set_theme(ThemeMode.LIGHT)
    
    def _detect_system_theme(self) -> ThemeMode:
        """Detecta o tema do sistema"""
        try:
            # Tenta usar darkdetect primeiro
            import darkdetect
            is_dark = darkdetect.isDark()
            logger.debug(f"Tema do sistema detectado via darkdetect: {'escuro' if is_dark else 'claro'}")
            return ThemeMode.DARK if is_dark else ThemeMode.LIGHT
        
        except ImportError:
            # Se darkdetect não estiver disponível, tenta outras alternativas
            try:
                import platform
                if platform.system() == "Windows":
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                        "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize") as key:
                        is_dark = not bool(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
                        logger.debug(f"Tema do sistema Windows detectado: {'escuro' if is_dark else 'claro'}")
                        return ThemeMode.DARK if is_dark else ThemeMode.LIGHT
            except:
                pass
            
            logger.warning("Não foi possível detectar o tema do sistema, usando tema claro como padrão")
            return ThemeMode.LIGHT
        
        except Exception as e:
            logger.error(f"Erro ao detectar tema do sistema: {e}")
            return ThemeMode.LIGHT
    
    def _get_theme_style(self) -> dict:
        """Obtém o estilo baseado no tema atual"""
        try:
            current = self.current_theme
            if current == ThemeMode.SYSTEM:
                system_theme = self._detect_system_theme()
                logger.debug(f"Tema do sistema detectado: {system_theme.value}")
                return THEME_STYLES[system_theme]
            return THEME_STYLES[current]
        except Exception as e:
            logger.error(f"Erro ao obter estilo do tema: {e}")
            # Fallback para tema claro em caso de erro
            return THEME_STYLES[ThemeMode.LIGHT]
    
    def _apply_theme(self):
        """Aplica o tema atual"""
        try:
            theme_style = self._get_theme_style()
            
            # Configura o tema do CustomTkinter
            if self.current_theme == ThemeMode.SYSTEM:
                ctk.set_appearance_mode("system")
            elif self.current_theme == ThemeMode.DARK:
                ctk.set_appearance_mode("dark")
            else:
                ctk.set_appearance_mode("light")
                
            # Define o tema de cores
            color_theme = dynamic_settings.get_window_setting('color_theme', 'blue')
            ctk.set_default_color_theme(color_theme)
            
            # Configura cores personalizadas
            self._configure_custom_colors(theme_style)
            
            # Notifica observadores após aplicar o tema
            self._notify_observers()
            
        except Exception as e:
            logger.error(f"Erro ao aplicar tema: {e}")
    
    def _configure_custom_colors(self, style: dict):
        """Configura cores personalizadas para widgets CTk"""
        try:
            # Define cores personalizadas para widgets específicos
            orange_colors = ["#FF8C00", "#FF6B00"]  # Laranja normal e hover
            text_color = style.get("text_color", ["#DCE4EE", "#DCE4EE"])
            
            # Botões em laranja
            ctk.ThemeManager.theme["CTkButton"]["fg_color"] = orange_colors
            ctk.ThemeManager.theme["CTkButton"]["hover_color"] = ["#E67E00", "#CC5500"]  # Laranja mais escuro para hover
            ctk.ThemeManager.theme["CTkButton"]["text_color"] = text_color
            
            # Títulos em laranja
            ctk.ThemeManager.theme["CTkLabel"]["text_color_button"] = orange_colors[0]  # Usa o primeiro tom de laranja
            
            # Entradas com borda laranja quando focadas
            ctk.ThemeManager.theme["CTkEntry"]["border_color_focused"] = orange_colors[0]
            
        except Exception as e:
            logger.error(f"Erro ao configurar cores personalizadas: {e}")

    def set_color_theme(self, color_theme: str) -> bool:
        """Define o tema de cores"""
        try:
            # Atualiza a configuração
            dynamic_settings.set_window_setting('color_theme', color_theme)
            # Aplica o tema
            ctk.set_default_color_theme(color_theme)
            # Notifica observadores
            self._notify_observers()
            
            logger.info(f"Tema de cores alterado para: {color_theme}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao alterar tema de cores: {e}")
            return False

# Instância global do gerenciador de temas
theme_manager = ThemeManager() 
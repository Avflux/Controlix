import customtkinter as ctk
from app.config.settings import dynamic_settings
import logging
from screeninfo import get_monitors

logger = logging.getLogger(__name__)

class WindowPositionMixin:
    """Mixin para gerenciar posição e tamanho das janelas"""
    
    def setup_window_position(self, window_name: str):
        """Configura a posição inicial da janela"""
        self.window_name = window_name
        self._configure_timer = None
        
        # Registra eventos de movimento e redimensionamento
        self.bind('<Configure>', self._on_window_configure)
        
        # Carrega posição salva ou centraliza
        if dynamic_settings.get_window_setting('remember_positions', True):
            self._load_window_position()
        else:
            self.center_window()
    
    def _on_window_configure(self, event=None):
        """Callback para mudanças na janela"""
        # Cancela timer anterior se existir
        if self._configure_timer is not None:
            self.after_cancel(self._configure_timer)
        
        # Agenda novo salvamento
        self._configure_timer = self.after(500, self._save_current_position)
    
    def _get_absolute_position(self):
        """Obtém a posição absoluta da janela na tela"""
        try:
            root_x = self.winfo_rootx()  # Posição X absoluta
            root_y = self.winfo_rooty()  # Posição Y absoluta
            return root_x, root_y
        except:
            return self.winfo_x(), self.winfo_y()
    
    def _save_current_position(self):
        """Salva a posição atual da janela"""
        try:
            x, y = self._get_absolute_position()
            width = self.winfo_width()
            height = self.winfo_height()
            
            dynamic_settings.save_window_position(
                self.window_name,
                x, y, width, height
            )
            logger.debug(f"Posição salva: {x},{y} {width}x{height}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar posição: {e}")
        finally:
            self._configure_timer = None
    
    def _get_current_monitor(self):
        """Obtém o monitor onde a janela está atualmente"""
        try:
            x, y = self._get_absolute_position()
            monitors = get_monitors()
            
            for monitor in monitors:
                if (monitor.x <= x < monitor.x + monitor.width and
                    monitor.y <= y < monitor.y + monitor.height):
                    return monitor
                    
            return monitors[0]  # Monitor principal como fallback
        except:
            return None
    
    def _load_window_position(self):
        """Carrega a última posição salva"""
        try:
            pos_data = dynamic_settings.get_window_position(self.window_name)
            if pos_data:
                x, y = pos_data['position']
                width, height = pos_data['size']
                
                # Verifica se a posição está em algum monitor
                monitors = get_monitors()
                visible = False
                
                for monitor in monitors:
                    if (x < monitor.x + monitor.width and 
                        x + width > monitor.x and
                        y < monitor.y + monitor.height and
                        y + height > monitor.y):
                        visible = True
                        break
                
                if visible:
                    self.geometry(f"{width}x{height}+{x}+{y}")
                    logger.debug(f"Posição restaurada: {x},{y} {width}x{height}")
                else:
                    self.center_window()
            else:
                self.center_window()
                
        except Exception as e:
            logger.error(f"Erro ao carregar posição: {e}")
            self.center_window()
    
    def center_window(self):
        """Centraliza a janela na tela atual"""
        try:
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            
            # Tenta obter o monitor atual ou usa o principal
            try:
                monitor = self._get_current_monitor() or get_monitors()[0]
                x = monitor.x + (monitor.width - width) // 2
                y = monitor.y + (monitor.height - height) // 2
            except:
                # Fallback para centralização simples
                x = (self.winfo_screenwidth() - width) // 2
                y = (self.winfo_screenheight() - height) // 2
            
            self.geometry(f"{width}x{height}+{x}+{y}")
            logger.debug(f"Janela centralizada: {x},{y} {width}x{height}")
            
        except Exception as e:
            logger.error(f"Erro ao centralizar: {e}") 
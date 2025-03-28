import sys
import tkinter as tk
import customtkinter as ctk
import traceback
from app.config.settings import APP_NAME
from app.ui.theme.theme_manager import theme_manager
from app.ui.notifications import notifications
from app.config.logging_config import initialize_logging, get_logger

# Inicializa todos os loggers primeiro
initialize_logging()

# Obtém o logger principal
logger = get_logger('app')

def main():
    try:
        print("Iniciando aplicação...")
        logger.info("Iniciando aplicação...")
        
        # Desabilita o scaling do DPI para melhor consistência entre monitores
        ctk.deactivate_automatic_dpi_awareness()
        ctk.set_window_scaling(1.0)  # Força escala 1:1
        ctk.set_widget_scaling(1.0)  # Força escala 1:1 para widgets
        
        # Cria e mostra a janela de login
        print("Importando e criando janela de login...")
        logger.info("Criando janela de login...")
        from app.ui.windows.login_window import LoginWindow
        login_window = LoginWindow()
        
        # Inicializa o gerenciador de temas
        print("Inicializando gerenciador de temas...")
        theme_manager.initialize()
        
        # Inicializa o gerenciador de notificações com a janela de login
        print("Inicializando gerenciador de notificações...")
        notifications.initialize(login_window)
        
        # Executa o loop principal
        print("Iniciando loop principal...")
        logger.info("Iniciando loop principal...")
        login_window.mainloop()
        
    except ImportError as e:
        error_msg = f"Erro ao importar módulos necessários: {e}"
        print(error_msg)
        print(traceback.format_exc())
        logger.error(error_msg, exc_info=True)
        sys.exit(1)
    except tk.TclError as e:
        error_msg = f"Erro na interface gráfica: {e}"
        print(error_msg)
        print(traceback.format_exc())
        logger.error(error_msg, exc_info=True)
        sys.exit(1)
    except Exception as e:
        error_msg = f"Erro inesperado ao iniciar aplicação: {e}"
        print(error_msg)
        print(traceback.format_exc())
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
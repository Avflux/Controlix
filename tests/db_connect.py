import sys
import os
import logging
import customtkinter as ctk
from threading import Thread

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connection import db
from config.encrypted_settings import EncryptedSettings

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

class DatabaseTester(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Teste de Conexão com Banco de Dados")
        self.geometry("600x400")
        
        # Centralizar a janela na tela
        self.center_window()
        
        # Criar widgets
        self.create_widgets()
        
    def center_window(self):
        """Centraliza a janela na tela"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 600
        window_height = 400
        
        # Calcula a posição x,y para centralizar
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
    def create_widgets(self):
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Teste de Conexão com Banco de Dados",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Botão de teste
        self.test_button = ctk.CTkButton(
            self.main_frame,
            text="Testar Conexão",
            command=self.start_test_connection
        )
        self.test_button.pack(pady=10)
        
        # Área de log
        self.log_text = ctk.CTkTextbox(
            self.main_frame,
            width=500,
            height=300
        )
        self.log_text.pack(pady=10)
        
    def log_message(self, message, level="INFO"):
        """Adiciona mensagem à área de log"""
        self.log_text.insert("end", f"[{level}] {message}\n")
        self.log_text.see("end")
        
    def start_test_connection(self):
        """Inicia o teste de conexão em uma thread separada"""
        self.test_button.configure(state="disabled")
        self.log_text.delete("1.0", "end")
        Thread(target=self.test_connection).start()
        
    def test_connection(self):
        """Testa a conexão com o banco de dados"""
        try:
            # Primeiro, vamos verificar as configurações
            self.log_message("Verificando configurações...")
            settings = EncryptedSettings()
            config = settings.decrypt_env()
            self.log_message(f"Configurações encontradas: {', '.join(config.keys())}")
            
            # Tenta obter conexão
            self.log_message("Tentando estabelecer conexão...")
            conn = db.get_connection()
            
            if conn:
                db_type = "MySQL" if db.is_mysql_available else "SQLite"
                self.log_message(f"Conexão estabelecida com sucesso usando {db_type}")
                
                # Testa uma query simples
                try:
                    result = db.execute_query("SELECT 1 as test")
                    self.log_message(f"Resultado da query: {result}")
                    
                    if result is not None:
                        self.log_message("Query de teste executada com sucesso")
                    else:
                        self.log_message("Query de teste falhou", "ERROR")
                        
                except Exception as e:
                    self.log_message(f"Erro ao executar query de teste: {e}", "ERROR")
                finally:
                    if db.is_mysql_available and conn:
                        conn.close()
            else:
                self.log_message("Não foi possível estabelecer conexão com nenhum banco de dados", "ERROR")
                self.log_message(f"Status MySQL: {db.is_mysql_available}", "DEBUG")
                self.log_message(f"Pool MySQL: {db.mysql_pool is not None}", "DEBUG")
                self.log_message(f"SQLite: {db.sqlite_conn is not None}", "DEBUG")
                
        except Exception as e:
            self.log_message(f"Erro durante teste de conexão: {e}", "ERROR")
        finally:
            self.log_message("Teste de conexão concluído")
            self.test_button.configure(state="normal")

if __name__ == "__main__":
    app = DatabaseTester()
    app.mainloop()

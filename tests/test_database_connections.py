import sys
import os
import logging
from pathlib import Path
import customtkinter as ctk
import keyring
from threading import Thread

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseTester(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Teste de Conexões com Banco de Dados")
        self.geometry("800x600")
        
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Teste de Conexões com Banco de Dados",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Status atual
        self.status_frame = ctk.CTkFrame(self.main_frame)
        self.status_frame.pack(pady=10, fill="x", padx=20)
        
        # MySQL Status
        self.mysql_status = ctk.CTkLabel(
            self.status_frame,
            text="MySQL: Verificando...",
            font=("Arial", 12)
        )
        self.mysql_status.pack(pady=5)
        
        # SQLite Status
        self.sqlite_status = ctk.CTkLabel(
            self.status_frame,
            text="SQLite: Verificando...",
            font=("Arial", 12)
        )
        self.sqlite_status.pack(pady=5)
        
        # Botões de teste
        self.buttons_frame = ctk.CTkFrame(self.main_frame)
        self.buttons_frame.pack(pady=20)
        
        # Botão de Inicialização
        self.init_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Inicializar Conexões",
            command=lambda: Thread(target=self.initialize_connections).start()
        )
        self.init_btn.pack(pady=5)
        
        # Teste MySQL
        self.mysql_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Testar MySQL",
            command=lambda: Thread(target=self.test_mysql).start(),
            state="disabled"  # Começa desabilitado
        )
        self.mysql_btn.pack(pady=5)
        
        # Teste SQLite
        self.sqlite_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Testar SQLite",
            command=lambda: Thread(target=self.test_sqlite).start(),
            state="disabled"  # Começa desabilitado
        )
        self.sqlite_btn.pack(pady=5)
        
        # Teste Fallback
        self.fallback_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Testar Fallback (MySQL → SQLite)",
            command=lambda: Thread(target=self.test_fallback).start(),
            state="disabled"  # Começa desabilitado
        )
        self.fallback_btn.pack(pady=5)
        
        # Limpar Credenciais MySQL
        self.clear_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Limpar Credenciais MySQL",
            command=lambda: Thread(target=self.clear_mysql_credentials).start(),
            fg_color="red"
        )
        self.clear_btn.pack(pady=5)
        
        # Área de log
        self.log_text = ctk.CTkTextbox(
            self.main_frame,
            width=700,
            height=300
        )
        self.log_text.pack(pady=10, padx=20)
        
        # Variáveis de estado
        self.db = None
        self.settings = None
        
    def initialize_connections(self):
        """Inicializa conexões de forma segura"""
        try:
            self.log_message("\n=== Inicializando conexões ===")
            
            # Importa módulos necessários
            from app.data.connection import DatabaseConnection
            from app.config.encrypted_settings import EncryptedSettings
            
            # Tenta inicializar configurações
            try:
                self.settings = EncryptedSettings()
                self.log_message("✓ Configurações inicializadas")
            except Exception as e:
                self.log_message(f"✗ Erro nas configurações: {e}")
                
            # Tenta inicializar conexão
            try:
                self.db = DatabaseConnection()
                self.log_message("✓ Gerenciador de conexões inicializado")
            except Exception as e:
                self.log_message(f"✗ Erro na conexão: {e}")
                
            # Atualiza status
            self.check_status()
            
            # Habilita botões de teste
            self.mysql_btn.configure(state="normal")
            self.sqlite_btn.configure(state="normal")
            self.fallback_btn.configure(state="normal")
            
        except Exception as e:
            self.log_message(f"✗ Erro na inicialização: {e}")
            
    def log_message(self, message: str):
        """Adiciona mensagem à área de log"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        logger.info(message)
        
    def check_status(self):
        """Verifica status atual das conexões"""
        try:
            # Verifica MySQL
            has_credentials = False
            try:
                if self.settings:
                    config = self.settings.decrypt_env()
                    has_credentials = all(k in config for k in ['DB_HOST', 'DB_USER', 'DB_PASSWORD'])
            except:
                pass
                
            mysql_status = "MySQL: "
            if has_credentials:
                mysql_status += "✓ Credenciais encontradas"
            else:
                mysql_status += "✗ Sem credenciais"
            self.mysql_status.configure(text=mysql_status)
            
            # Verifica SQLite
            sqlite_status = "SQLite: "
            if self.db and self.db.sqlite_pool:
                sqlite_status += "✓ Disponível"
            else:
                sqlite_status += "✗ Indisponível"
            self.sqlite_status.configure(text=sqlite_status)
            
        except Exception as e:
            self.log_message(f"Erro ao verificar status: {e}")
            
    def test_mysql(self):
        """Testa conexão MySQL"""
        try:
            self.log_message("\n=== Testando conexão MySQL ===")
            
            # Força usar MySQL
            if not self.db.is_mysql_available:
                self.log_message("MySQL não está disponível")
                return
                
            # Testa query
            result = self.db.execute_query("SELECT 1 as test")
            if result and result[0]['test'] == 1:
                self.log_message("✓ Conexão MySQL funcionando")
            else:
                self.log_message("✗ Erro na query MySQL")
                
        except Exception as e:
            self.log_message(f"✗ Erro ao testar MySQL: {e}")
            
    def test_sqlite(self):
        """Testa conexão SQLite"""
        try:
            self.log_message("\n=== Testando conexão SQLite ===")
            
            # Força usar SQLite
            original_mysql = self.db.is_mysql_available
            self.db.is_mysql_available = False
            
            try:
                # Testa query
                result = self.db.execute_query("SELECT 1 as test")
                if result and result[0]['test'] == 1:
                    self.log_message("✓ Conexão SQLite funcionando")
                else:
                    self.log_message("✗ Erro na query SQLite")
            finally:
                self.db.is_mysql_available = original_mysql
                
        except Exception as e:
            self.log_message(f"✗ Erro ao testar SQLite: {e}")
            
    def test_fallback(self):
        """Testa fallback para SQLite"""
        try:
            self.log_message("\n=== Testando fallback para SQLite ===")
            
            # Desativa MySQL temporariamente
            original_mysql = self.db.is_mysql_available
            self.db.is_mysql_available = False
            
            try:
                # Deve usar SQLite automaticamente
                result = self.db.execute_query("SELECT 1 as test")
                if result and result[0]['test'] == 1:
                    self.log_message("✓ Fallback para SQLite funcionou")
                else:
                    self.log_message("✗ Erro no fallback")
            finally:
                self.db.is_mysql_available = original_mysql
                
        except Exception as e:
            self.log_message(f"✗ Erro ao testar fallback: {e}")
            
    def clear_mysql_credentials(self):
        """Remove credenciais MySQL do keyring"""
        try:
            self.log_message("\n=== Removendo credenciais MySQL ===")
            
            credentials = [
                ('controlix', 'CRYPTO_KEY'),
                ('controlix', 'ENV_DATA')
            ]
            
            for service, key in credentials:
                try:
                    if keyring.get_password(service, key):
                        keyring.delete_password(service, key)
                        self.log_message(f"✓ Removida credencial: {service}/{key}")
                    else:
                        self.log_message(f"- Credencial não encontrada: {service}/{key}")
                except Exception as e:
                    self.log_message(f"✗ Erro ao remover {service}/{key}: {e}")
                    
            self.log_message("Limpeza concluída!")
            self.check_status()
            
        except Exception as e:
            self.log_message(f"✗ Erro durante limpeza: {e}")

def main():
    app = DatabaseTester()
    app.mainloop()

if __name__ == "__main__":
    main() 
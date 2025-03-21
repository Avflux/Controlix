import sys
import os
import logging
from pathlib import Path
import keyring
import customtkinter as ctk

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KeyringCleaner(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Limpar Credenciais do Keyring")
        self.geometry("500x400")
        
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Limpeza de Credenciais do Sistema",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Aviso
        self.warning_label = ctk.CTkLabel(
            self.main_frame,
            text="ATENÇÃO: Esta operação irá remover todas as credenciais\n"
                 "armazenadas no keyring do sistema para este aplicativo.\n"
                 "Certifique-se de ter um backup antes de continuar.",
            text_color="red"
        )
        self.warning_label.pack(pady=20)
        
        # Botões
        self.clear_btn = ctk.CTkButton(
            self.main_frame,
            text="Limpar Credenciais",
            command=self.clear_keyring,
            fg_color="red"
        )
        self.clear_btn.pack(pady=10)
        
        # Log area
        self.log_text = ctk.CTkTextbox(
            self.main_frame,
            width=400,
            height=200
        )
        self.log_text.pack(pady=10)
        
    def log_message(self, message: str):
        """Adiciona mensagem à área de log"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        logger.info(message)
        
    def clear_keyring(self):
        """Limpa todas as credenciais do keyring"""
        try:
            # Lista de credenciais para remover
            credentials = [
                ('controlix', 'CRYPTO_KEY'),
                ('controlix', 'ENV_DATA'),
                ('controlix', 'SQLITE_KEY')
            ]
            
            self.log_message("Iniciando limpeza do keyring...")
            
            for service, key in credentials:
                try:
                    # Verifica se existe
                    value = keyring.get_password(service, key)
                    if value:
                        # Remove a credencial
                        keyring.delete_password(service, key)
                        self.log_message(f"✓ Removida credencial: {service}/{key}")
                    else:
                        self.log_message(f"- Credencial não encontrada: {service}/{key}")
                except Exception as e:
                    self.log_message(f"✗ Erro ao remover {service}/{key}: {e}")
            
            self.log_message("\nLimpeza concluída!")
            
        except Exception as e:
            self.log_message(f"\nErro durante limpeza: {e}")
            logger.error(f"Erro ao limpar keyring: {e}", exc_info=True)

def main():
    app = KeyringCleaner()
    app.mainloop()

if __name__ == "__main__":
    main() 
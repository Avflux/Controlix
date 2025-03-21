import logging
import platform
import json
from pathlib import Path
from typing import Optional, Dict
import customtkinter as ctk
from typing import Callable

logger = logging.getLogger(__name__)

class SecureStorageGUI(ctk.CTkFrame):
    def __init__(self, master, storage: 'SecureStorage', callback: Callable = None):
        super().__init__(master)
        self.storage = storage
        self.callback = callback
        
        # Configuração do layout
        self.grid_columnconfigure(0, weight=1)
        
        # Labels e campos
        self.title = ctk.CTkLabel(self, text="Configuração de Credenciais", font=("Roboto", 16, "bold"))
        self.title.grid(row=0, column=0, pady=10, padx=10, sticky="ew")
        
        # Frame para os campos
        self.fields_frame = ctk.CTkFrame(self)
        self.fields_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.fields_frame.grid_columnconfigure(1, weight=1)
        
        # Campos de entrada
        self.entries = {}
        self.create_credential_fields()
        
        # Botões
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.save_btn = ctk.CTkButton(
            self.button_frame, 
            text="Salvar Credenciais",
            command=self.save_credentials
        )
        self.save_btn.pack(side="left", padx=5)
        
        self.delete_btn = ctk.CTkButton(
            self.button_frame,
            text="Excluir Credenciais",
            command=self.delete_credentials,
            fg_color="red",
            hover_color="darkred"
        )
        self.delete_btn.pack(side="right", padx=5)
        
        # Carregar credenciais existentes
        self.load_existing_credentials()

    def create_credential_fields(self):
        # Adicione seus campos de credenciais aqui
        fields = ["host", "database", "user", "password", "port"]
        
        for i, field in enumerate(fields):
            label = ctk.CTkLabel(self.fields_frame, text=field.capitalize() + ":")
            label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            if field == "password":
                entry = ctk.CTkEntry(self.fields_frame, show="*")
            else:
                entry = ctk.CTkEntry(self.fields_frame)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[field] = entry

    def load_existing_credentials(self):
        credentials = self.storage.get_credentials()
        if credentials:
            for field, value in credentials.items():
                if field in self.entries:
                    self.entries[field].delete(0, "end")
                    self.entries[field].insert(0, str(value))

    def save_credentials(self):
        credentials = {}
        for field, entry in self.entries.items():
            credentials[field] = entry.get()
        
        if self.storage.save_credentials(credentials):
            if self.callback:
                self.callback(credentials)
                
            # Mostrar mensagem de sucesso
            self.show_message("Sucesso", "Credenciais salvas com sucesso!")
        else:
            self.show_message("Erro", "Erro ao salvar credenciais!", "error")

    def delete_credentials(self):
        if self.storage.delete_credentials():
            for entry in self.entries.values():
                entry.delete(0, "end")
            self.show_message("Sucesso", "Credenciais excluídas com sucesso!")
        else:
            self.show_message("Erro", "Erro ao excluir credenciais!", "error")

    def show_message(self, title: str, message: str, level: str = "info"):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        label = ctk.CTkLabel(dialog, text=message)
        label.pack(pady=20)
        
        btn = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
        btn.pack(pady=10)

class SecureStorage:
    def __init__(self):
        self.system = platform.system()
        self.app_name = "Controlix"
        self.credential_key = "mysql_credentials"
        self._storage_available = False
        self._keyring = None
        self._win32cred = None
        
        try:
            if self.system == "Windows":
                try:
                    from win32 import win32cred
                    self._win32cred = win32cred
                    self._storage_available = True
                except ImportError as e:
                    logger.warning(f"pywin32 não encontrado: {e}. Instale com: pip install pywin32")
                    self._storage_available = False
            else:
                try:
                    import keyring
                    self._keyring = keyring
                    # Testa se o keyring está funcionando
                    keyring.get_keyring()
                    self._storage_available = True
                except (ImportError, RuntimeError) as e:
                    logger.warning(f"Erro ao inicializar keyring: {e}. Instale com: pip install keyring")
                    self._storage_available = False
        except Exception as e:
            logger.error(f"Erro ao inicializar armazenamento seguro: {e}")
            self._storage_available = False
    
    def is_available(self) -> bool:
        """Verifica se o armazenamento seguro está disponível"""
        return self._storage_available
    
    def save_credentials(self, credentials: Dict) -> bool:
        """Salva as credenciais no armazenamento seguro do sistema"""
        if not self._storage_available:
            logger.warning("Armazenamento seguro não disponível")
            return False
            
        try:
            # Converte para string JSON
            cred_str = json.dumps(credentials)
            
            if self.system == "Windows":
                try:
                    target = f"{self.app_name}_{self.credential_key}"
                    
                    # No Windows, precisamos usar string diretamente
                    credential = {
                        'Type': 1,  # CRED_TYPE_GENERIC
                        'TargetName': target,
                        'UserName': self.app_name,
                        'CredentialBlob': cred_str,  # Usa string diretamente
                        'Persist': 2,  # LOCAL_MACHINE
                        'Comment': 'Controlix Database Credentials'
                    }
                    
                    self._win32cred.CredWrite(credential, 0)
                    logger.debug("Credenciais salvas no Windows Credential Manager")
                    
                except Exception as e:
                    logger.error(f"Erro ao salvar no Windows Credential Manager: {e}")
                    return False
            else:
                self._keyring.set_password(self.app_name, self.credential_key, cred_str)
                logger.debug("Credenciais salvas no keyring")
            
            logger.info("Credenciais salvas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar credenciais: {e}")
            return False
    
    def get_credentials(self) -> Optional[Dict]:
        """Recupera as credenciais do armazenamento seguro"""
        if not self._storage_available:
            return None
            
        try:
            if self.system == "Windows":
                try:
                    target = f"{self.app_name}_{self.credential_key}"
                    cred = self._win32cred.CredRead(target, 1)  # CRED_TYPE_GENERIC
                    
                    # No Windows, o CredentialBlob já vem como string
                    cred_str = cred['CredentialBlob']
                    if isinstance(cred_str, bytes):
                        cred_str = cred_str.decode('utf-16-le')
                    
                except Exception as e:
                    logger.debug(f"Nenhuma credencial encontrada no Windows: {e}")
                    return None
            else:
                cred_str = self._keyring.get_password(self.app_name, self.credential_key)
                if not cred_str:
                    return None
            
            return json.loads(cred_str)
            
        except Exception as e:
            logger.error(f"Erro ao recuperar credenciais: {e}")
            return None
    
    def delete_credentials(self) -> bool:
        """Remove as credenciais do armazenamento seguro"""
        if not self._storage_available:
            return False
            
        try:
            if self.system == "Windows":
                try:
                    target = f"{self.app_name}_{self.credential_key}"
                    self._win32cred.CredDelete(target, 1)  # CRED_TYPE_GENERIC
                except Exception:
                    pass
            else:
                try:
                    self._keyring.delete_password(self.app_name, self.credential_key)
                except Exception:
                    pass
            return True
        except Exception:
            return False 
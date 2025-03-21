import logging
import customtkinter as ctk
from cryptography.fernet import Fernet
from pathlib import Path
from .secure_storage import SecureStorage
from typing import Optional
import base64
from app.config.settings import SECURITY_SETTINGS, SECURITY_DIR
import keyring
import os
import time

# Logger específico para configurações criptografadas
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Exceção personalizada para erros de configuração"""
    pass

class EncryptedSettingsGUI(ctk.CTkFrame):
    def __init__(self, master: Optional[ctk.CTk] = None):
        if not master:
            self.window = ctk.CTk()
            master = self.window
            self.window.title("Configurações Criptografadas")
            self.window.geometry("600x400")
        super().__init__(master)
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.settings = EncryptedSettings()
        self._create_widgets()
        self._load_current_settings()

    def _create_widgets(self):
        # Frame para campos de entrada
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Campos de configuração
        self.fields = {}
        config_fields = [
            ('DB_HOST', 'Host do Banco:'),
            ('DB_USER', 'Usuário:'),
            ('DB_PASSWORD', 'Senha:', True),
            ('DB_NAME', 'Nome do Banco:'),
            ('DB_PORT', 'Porta:')
        ]

        for i, (key, label, *opts) in enumerate(config_fields):
            show = "•" if opts and opts[0] else None
            lbl = ctk.CTkLabel(self.input_frame, text=label)
            lbl.grid(row=i, column=0, padx=5, pady=5, sticky="e")
            
            entry = ctk.CTkEntry(self.input_frame, show=show, width=200)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.fields[key] = entry

        # Botões
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(fill="x", padx=5, pady=5)

        self.save_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Salvar Configurações",
            command=self._save_settings
        )
        self.save_btn.pack(side="left", padx=5)

        self.load_btn = ctk.CTkButton(
            self.btn_frame,
            text="Carregar Configurações",
            command=self._load_current_settings
        )
        self.load_btn.pack(side="left", padx=5)

    def _load_current_settings(self):
        try:
            config = self.settings.decrypt_env()
            for key, entry in self.fields.items():
                value = config.get(key, "")
                entry.delete(0, "end")
                entry.insert(0, str(value))
        except Exception as e:
            self._show_error(f"Erro ao carregar configurações: {str(e)}")

    def _save_settings(self):
        try:
            config = {key: entry.get() for key, entry in self.fields.items()}
            self.settings.encrypt_env(config)
            self._show_info("Configurações salvas com sucesso!")
        except Exception as e:
            self._show_error(f"Erro ao salvar configurações: {str(e)}")

    def _show_error(self, message: str):
        ctk.CTkMessagebox(
            title="Erro",
            message=message,
            icon="cancel"
        )

    def _show_info(self, message: str):
        ctk.CTkMessagebox(
            title="Sucesso",
            message=message,
            icon="check"
        )

class EncryptedSettings:
    def __init__(self):
        """Inicializa o gerenciador de configurações criptografadas"""
        try:
            logger.info("Iniciando configurações criptografadas")
            
            # Configura caminhos
            self.key_file = SECURITY_DIR / 'crypto.key'
            self.env_file = SECURITY_DIR / '.env.encrypted'
            
            # Cache para evitar descriptografar repetidamente
            self._env_cache = None
            self._last_backup_time = 0
            
            # Carrega configurações e move para keyring
            self._process_and_secure_settings()
            
            self.secure_storage = SecureStorage()
            
        except ConfigError as ce:
            logger.error(f"Erro de configuração: {ce}")
            self._show_config_error(
                "Arquivos de Configuração Ausentes",
                "Para iniciar o sistema pela primeira vez, são necessários os arquivos:\n\n"
                f"• {self.key_file.name}\n"
                f"• {self.env_file.name}\n\n"
                "Estes arquivos devem estar no diretório:\n"
                f"{SECURITY_DIR}\n\n"
                "Por favor, configure o sistema usando o aplicativo de configuração."
            )
            raise
        except Exception as e:
            logger.critical("Falha na inicialização de segurança", exc_info=True)
            self._show_config_error(
                "Erro de Inicialização",
                "Ocorreu um erro ao inicializar o sistema de segurança.\n\n"
                f"Erro: {str(e)}\n\n"
                "Verifique os logs para mais detalhes."
            )
            raise ConfigError("Não foi possível inicializar sistema de segurança") from e

    def _process_and_secure_settings(self):
        """Processa arquivos e faz backup no keyring"""
        try:
            # Evitar backups frequentes (no máximo a cada 1 hora)
            current_time = time.time()
            if current_time - self._last_backup_time < 3600:
                logger.debug("Backup recente já realizado, pulando")
                return
                
            # Se existem arquivos, faz backup no keyring
            if self.key_file.exists() and self.env_file.exists():
                logger.info("Fazendo backup das configurações no keyring")
                
                # Lê e armazena no keyring como backup
                crypto_key = self.key_file.read_text().strip()
                env_data = self.env_file.read_text().strip()
                
                keyring.set_password('controlix', 'CRYPTO_KEY', crypto_key)
                keyring.set_password('controlix', 'ENV_DATA', env_data)
                
                self._last_backup_time = current_time
                logger.info("Backup das configurações realizado no keyring")
                return
                
            # Se não existem arquivos, tenta usar keyring
            crypto_key = keyring.get_password('controlix', 'CRYPTO_KEY')
            env_data = keyring.get_password('controlix', 'ENV_DATA')
            
            if not (crypto_key and env_data):
                raise ConfigError("Configurações não encontradas no sistema")
                
        except Exception as e:
            logger.error("Erro ao processar configurações", exc_info=True)
            raise

    def _secure_delete(self, path: Path):
        """Remove arquivo de forma segura"""
        try:
            if path.exists():
                # Sobrescreve com dados aleatórios
                with open(path, 'wb') as f:
                    f.write(os.urandom(path.stat().st_size))
                # Remove o arquivo
                path.unlink()
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo {path}: {e}")

    def _get_fernet(self) -> Fernet:
        """Obtém instância do Fernet usando a chave do keyring"""
        try:
            crypto_key = keyring.get_password('controlix', 'CRYPTO_KEY')
            if not crypto_key:
                raise ConfigError("Chave criptográfica não encontrada no keyring")
            return Fernet(crypto_key.encode())
        except Exception as e:
            logger.error(f"Erro ao criar Fernet: {e}", exc_info=True)
            raise ConfigError("Erro ao obter chave de criptografia") from e
    
    def decrypt_env(self) -> dict:
        """Descriptografa e retorna as configurações do ambiente"""
        # Retorna o cache se disponível
        if self._env_cache is not None:
            return self._env_cache
            
        try:
            # Primeiro tenta usar os arquivos
            if self.key_file.exists() and self.env_file.exists():
                logger.debug("Usando arquivos de configuração do diretório .security")
                
                # Lê e descriptografa dos arquivos
                with open(self.key_file, 'r') as f:
                    crypto_key = f.read().strip()
                with open(self.env_file, 'rb') as f:
                    env_data = f.read()
                    
            else:
                # Se não encontrou arquivos, tenta usar keyring
                logger.debug("Arquivos não encontrados, usando backup do keyring")
                crypto_key = keyring.get_password('controlix', 'CRYPTO_KEY')
                env_data = keyring.get_password('controlix', 'ENV_DATA')
                
                if not (crypto_key and env_data):
                    raise ConfigError("Configurações não encontradas no sistema")
                env_data = env_data.encode('latin1')

            # Descriptografa os dados
            f = Fernet(crypto_key.encode())
            try:
                decrypted_data = f.decrypt(env_data).decode()
            except Exception as e:
                logger.error(f"Erro ao descriptografar dados: {e}")
                raise ConfigError("Dados corrompidos ou chave inválida")

            # Converte para dicionário
            env_dict = {}
            for line in decrypted_data.split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_dict[key.strip()] = value.strip()
            
            # Armazena no cache
            self._env_cache = env_dict
            return env_dict
            
        except Exception as e:
            logger.error(f"Falha ao obter configurações: {e}", exc_info=True)
            raise ConfigError("Não foi possível obter as configurações") from e

    def encrypt_env(self, config_dict: dict):
        """Criptografa e salva as configurações apenas no keyring"""
        try:
            f = self._get_fernet()
            
            # Converte e criptografa
            env_content = "\n".join([f"{k}={v}" for k, v in config_dict.items()])
            encrypted_data = f.encrypt(env_content.encode())
            
            # Salva apenas no keyring
            keyring.set_password('controlix', 'ENV_DATA', 
                               encrypted_data.decode('latin1'))
            
            # Atualiza o cache
            self._env_cache = config_dict
            self._last_backup_time = time.time()
            
            logger.info("Configurações salvas com sucesso no keyring")
            
        except Exception as e:
            logger.error(f"Erro ao criptografar configurações: {e}")
            raise ConfigError(f"Erro ao salvar configurações: {str(e)}")

    def set_secure_setting(self, key: str, value: bytes):
        """Armazena uma configuração de forma segura"""
        try:
            # Converte bytes para string base64 para armazenamento
            if isinstance(value, bytes):
                value = base64.b64encode(value).decode('utf-8')
            
            self.secure_storage.set_password(
                'controlix',  # Aplicação
                key,         # Identificador da configuração
                value       # Valor a ser armazenado
            )
            logger.debug(f"Configuração {key} armazenada com segurança")
            
        except Exception as e:
            logger.error(f"Erro ao armazenar configuração segura: {e}")
            raise

    def get_secure_setting(self, key: str) -> Optional[bytes]:
        """Obtém uma configuração segura do keyring"""
        try:
            return keyring.get_password("controlix", key)
        except Exception as e:
            logger.error(f"Erro ao obter configuração segura '{key}': {e}")
            return None
            
    def get(self, key: str, default=None) -> str:
        """Obtém uma configuração do ambiente criptografado"""
        try:
            env_dict = self.decrypt_env()
            return env_dict.get(key, default)
        except Exception as e:
            logger.error(f"Erro ao obter configuração '{key}': {e}")
            return default

    def _show_config_error(self, title: str, message: str):
        """Exibe mensagem de erro de configuração"""
        try:
            from customtkinter import CTkMessagebox
            CTkMessagebox(
                title=title,
                message=message,
                icon="cancel",
                option_1="OK"
            )
        except Exception as e:
            # Fallback para messagebox do tkinter se CTk falhar
            try:
                from tkinter import messagebox
                messagebox.showerror(title, message)
            except:
                # Se tudo falhar, apenas loga o erro
                logger.error(f"{title}: {message}")

def load_settings():
    """Carrega as configurações e retorna as configurações ou raise exception"""
    try:
        encrypted_settings = EncryptedSettings()
        env_config = encrypted_settings.decrypt_env()
        
        # Mapeamento entre prefixos MYSQL_ e DB_
        config_mapping = {
            'DB_HOST': ['DB_HOST', 'MYSQL_HOST'],
            'DB_USER': ['DB_USER', 'MYSQL_USER'],
            'DB_PASSWORD': ['DB_PASSWORD', 'MYSQL_PASSWORD'],
            'DB_NAME': ['DB_NAME', 'MYSQL_DATABASE'],
            'DB_PORT': ['DB_PORT', 'MYSQL_PORT'],
        }

        # Converter configurações MYSQL_ para o formato DB_
        normalized_config = {}
        for db_key, possible_keys in config_mapping.items():
            value = None
            for key in possible_keys:
                if key in env_config:
                    value = env_config[key]
                    break
            if value is not None:
                normalized_config[db_key] = value

        # Verifica configurações obrigatórias
        required_configs = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        missing_configs = [config for config in required_configs if config not in normalized_config]
        
        if missing_configs:
            error_msg = (f"Configurações ausentes: {', '.join(missing_configs)}\n"
                        f"Configurações encontradas: {', '.join(env_config.keys())}")
            logger.error(error_msg)
            raise ConfigError(error_msg)

        # Log das configurações carregadas (sem senhas)
        safe_config = {k: v if 'PASSWORD' not in k else '***' for k, v in normalized_config.items()}
        logger.info(f"Configurações normalizadas carregadas: {safe_config}")
        
        return {
            'DB_CONFIG': {
                'host': normalized_config['DB_HOST'],
                'user': normalized_config['DB_USER'],
                'password': normalized_config['DB_PASSWORD'],
                'database': normalized_config['DB_NAME'],
                'port': int(normalized_config.get('DB_PORT', 3306))
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")
        raise 

if __name__ == "__main__":
    app = EncryptedSettingsGUI()
    app.window.mainloop() 

# Instância global para uso em outros módulos
encrypted_settings = EncryptedSettings() 
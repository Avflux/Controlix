import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
from app.config.settings import PROJECT_DIRS, DATABASE, BACKUP_SETTINGS
from app.config.secure_storage import SecureStorage
import zipfile
from typing import Optional
import time
import subprocess

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.backup_dir = PROJECT_DIRS['backups']
        self.secure_storage = SecureStorage()
        self.settings = BACKUP_SETTINGS
        
    def create_backup(self, backup_type: str = 'full'):
        """Cria um backup do sistema"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            # Backup do banco MySQL
            self._backup_mysql(backup_path)
            
            # Backup das configurações
            if backup_type == 'full':
                self._backup_settings(backup_path)
                self._backup_migrations(backup_path)
            
            # Compacta o backup
            zip_file = self._compress_backup(backup_path)
            
            # Remove o diretório temporário
            shutil.rmtree(backup_path)
            
            logger.info(f"Backup criado com sucesso: {zip_file}")
            return zip_file
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}", exc_info=True)
            raise
    
    def _backup_mysql(self, backup_path: Path):
        """Backup do banco MySQL"""
        try:
            # Cria diretório para banco
            db_backup_dir = backup_path / 'database'
            db_backup_dir.mkdir(exist_ok=True)
            
            # Obtém credenciais do MySQL
            credentials = self.secure_storage.get_credentials()
            if not credentials:
                logger.warning("Credenciais MySQL não encontradas")
                return
            
            # Cria arquivo de configuração para mysqldump
            config_file = db_backup_dir / 'my.cnf'
            with open(config_file, 'w') as f:
                f.write(f"[client]\n")
                f.write(f"user={credentials.get('username', '')}\n")
                f.write(f"password={credentials.get('password', '')}\n")
                f.write(f"host={credentials.get('host', 'localhost')}\n")
                f.write(f"port={credentials.get('port', '3306')}\n")
            
            # Define caminho para o arquivo de backup
            backup_file = db_backup_dir / f"{credentials.get('database', 'controlix_local')}.sql"
            
            # Executa o comando mysqldump
            cmd = [
                "mysqldump",
                f"--defaults-file={config_file}",
                "--single-transaction",
                "--routines",
                "--triggers",
                "--events",
                credentials.get('database', 'controlix_local')
            ]
            
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            # Remove arquivo de configuração temporário
            config_file.unlink()
            
            logger.debug(f"Backup do banco MySQL realizado: {backup_file}")
            
        except Exception as e:
            logger.error(f"Erro no backup do MySQL: {e}")
            raise
    
    def _backup_settings(self, backup_path: Path):
        """Backup das configurações"""
        try:
            settings_dir = backup_path / 'settings'
            settings_dir.mkdir(exist_ok=True)
            
            # Backup do user_settings.json
            user_settings = PROJECT_DIRS['data']['path'] / 'user_settings.json'
            if user_settings.exists():
                shutil.copy2(user_settings, settings_dir)
            
            # Backup de outras configurações importantes
            config_files = {
                'icon_mapping.json': PROJECT_DIRS['root'] / 'config' / 'icon_mapping.json',
                # Adicionar outros arquivos de configuração conforme necessário
            }
            
            for name, path in config_files.items():
                if path.exists():
                    shutil.copy2(path, settings_dir / name)
                    
            logger.debug("Backup das configurações realizado")
            
        except Exception as e:
            logger.error(f"Erro no backup das configurações: {e}")
            raise
    
    def _backup_migrations(self, backup_path: Path):
        """Backup das migrações pendentes"""
        try:
            migrations_dir = PROJECT_DIRS['data']['subdirs']['migrations']
            if migrations_dir.exists():
                backup_migrations = backup_path / 'migrations'
                shutil.copytree(migrations_dir, backup_migrations)
                logger.debug("Backup das migrações realizado")
                
        except Exception as e:
            logger.error(f"Erro no backup das migrações: {e}")
            raise
    
    def _compress_backup(self, backup_path: Path):
        """Compacta o backup em ZIP"""
        try:
            zip_path = backup_path.with_suffix('.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in backup_path.rglob('*'):
                    if file.is_file():
                        zipf.write(file, file.relative_to(backup_path))
            
            # Remove diretório original após compactação
            shutil.rmtree(backup_path)
            logger.debug(f"Backup compactado: {zip_path.name}")
            
            return zip_path.name
            
        except Exception as e:
            logger.error(f"Erro ao compactar backup: {e}")
            raise
    
    def restore_backup(self, backup_file: Path):
        """Restaura um backup"""
        try:
            if not backup_file.exists():
                raise FileNotFoundError(f"Arquivo de backup não encontrado: {backup_file}")
            
            # Cria diretório temporário para extração
            temp_dir = self.backup_dir / f"temp_restore_{int(time.time())}"
            temp_dir.mkdir(exist_ok=True)
            
            # Extrai o backup
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Restaura o banco MySQL
            self._restore_mysql(temp_dir)
            
            # Restaura as configurações
            self._restore_settings(temp_dir)
            
            # Remove diretório temporário
            shutil.rmtree(temp_dir)
            
            logger.info(f"Backup restaurado com sucesso: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}", exc_info=True)
            return False
    
    def _restore_mysql(self, backup_path: Path):
        """Restaura o banco MySQL"""
        try:
            # Verifica se existe diretório de banco
            db_backup_dir = backup_path / 'database'
            if not db_backup_dir.exists():
                logger.warning("Diretório de backup do banco não encontrado")
                return
            
            # Obtém credenciais do MySQL
            credentials = self.secure_storage.get_credentials()
            if not credentials:
                logger.warning("Credenciais MySQL não encontradas")
                return
            
            # Procura arquivo SQL de backup
            sql_files = list(db_backup_dir.glob('*.sql'))
            if not sql_files:
                logger.warning("Nenhum arquivo SQL encontrado no backup")
                return
            
            backup_file = sql_files[0]
            
            # Cria arquivo de configuração para mysql
            config_file = db_backup_dir / 'my.cnf'
            with open(config_file, 'w') as f:
                f.write(f"[client]\n")
                f.write(f"user={credentials.get('username', '')}\n")
                f.write(f"password={credentials.get('password', '')}\n")
                f.write(f"host={credentials.get('host', 'localhost')}\n")
                f.write(f"port={credentials.get('port', '3306')}\n")
            
            # Executa o comando mysql para restaurar
            cmd = [
                "mysql",
                f"--defaults-file={config_file}",
                credentials.get('database', 'controlix_local')
            ]
            
            with open(backup_file, 'r') as f:
                subprocess.run(cmd, stdin=f, check=True)
            
            # Remove arquivo de configuração temporário
            config_file.unlink()
            
            logger.debug(f"Banco MySQL restaurado a partir de: {backup_file}")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar banco MySQL: {e}")
            raise
    
    def _restore_settings(self, backup_path: Path):
        """Restaura as configurações"""
        try:
            settings_dir = backup_path / 'settings'
            if not settings_dir.exists():
                logger.warning("Diretório de configurações não encontrado no backup")
                return
            
            # Restaura user_settings.json
            user_settings_backup = settings_dir / 'user_settings.json'
            if user_settings_backup.exists():
                user_settings_dest = PROJECT_DIRS['data']['path'] / 'user_settings.json'
                shutil.copy2(user_settings_backup, user_settings_dest)
                logger.debug("Arquivo user_settings.json restaurado")
            
            # Restaura outras configurações
            config_files = {
                'icon_mapping.json': PROJECT_DIRS['root'] / 'config' / 'icon_mapping.json',
                # Adicionar outros arquivos de configuração conforme necessário
            }
            
            for name, dest_path in config_files.items():
                backup_file = settings_dir / name
                if backup_file.exists():
                    shutil.copy2(backup_file, dest_path)
                    logger.debug(f"Arquivo {name} restaurado")
            
            logger.debug("Configurações restauradas com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar configurações: {e}")
            raise
    
    def manage_backups(self):
        """Gerencia backups automáticos e rotação"""
        try:
            if not self.settings['auto_backup']['enabled']:
                return
                
            now = datetime.now()
            last_backup = self._get_last_backup_time()
            
            # Verifica se é hora de fazer backup
            if self._should_create_backup(last_backup):
                logger.info("Iniciando backup automático...")
                self.create_backup('full')
                
            # Rotação de backups antigos
            self._rotate_old_backups()
                
        except Exception as e:
            logger.error(f"Erro ao gerenciar backups: {e}")
    
    def _get_last_backup_time(self) -> Optional[datetime]:
        """Obtém a data/hora do último backup"""
        try:
            backup_files = list(self.backup_dir.glob('backup_*.zip'))
            if not backup_files:
                return None
                
            # Ordena por data de modificação (mais recente primeiro)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Retorna timestamp do arquivo mais recente
            return datetime.fromtimestamp(backup_files[0].stat().st_mtime)
            
        except Exception as e:
            logger.error(f"Erro ao obter data do último backup: {e}")
            return None
    
    def _should_create_backup(self, last_backup: Optional[datetime]) -> bool:
        """Verifica se deve criar um novo backup"""
        if not last_backup:
            return True
            
        now = datetime.now()
        interval_hours = self.settings['auto_backup'].get('interval', 24)
        
        # Calcula próximo backup programado
        next_backup = last_backup + timedelta(hours=interval_hours)
        
        return now >= next_backup
    
    def _rotate_old_backups(self):
        """Remove backups antigos conforme política de retenção"""
        try:
            backup_files = list(self.backup_dir.glob('backup_*.zip'))
            if not backup_files:
                return
                
            # Ordena por data de modificação (mais antigo primeiro)
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            
            # Obtém configurações de retenção
            max_backups = self.settings.get('max_backups', 10)
            keep_days = self.settings['auto_backup'].get('keep_days', 30)
            
            # Remove backups excedentes
            if len(backup_files) > max_backups:
                files_to_remove = backup_files[:-max_backups]
                for file in files_to_remove:
                    file.unlink()
                    logger.debug(f"Backup antigo removido: {file.name}")
            
            # Remove backups mais antigos que o período de retenção
            now = datetime.now()
            cutoff_date = now - timedelta(days=keep_days)
            
            for file in backup_files:
                file_date = datetime.fromtimestamp(file.stat().st_mtime)
                if file_date < cutoff_date:
                    file.unlink()
                    logger.debug(f"Backup expirado removido: {file.name}")
                    
        except Exception as e:
            logger.error(f"Erro ao rotacionar backups: {e}") 
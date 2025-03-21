import logging
import logging.handlers
from pathlib import Path
from typing import Dict
from .settings import LOGS_DIR

def setup_logger(name: str, log_file: Path, level=logging.INFO, console_level=logging.ERROR) -> logging.Logger:
    """Configura um logger específico com rotação de arquivos"""
    
    # Garante que o diretório de logs existe
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Cria o logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evita duplicação de handlers
    if not logger.handlers:
        # Handler para arquivo com rotação
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Handler para console com nível mais restritivo
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)  # Apenas ERROR e acima no console
        
        # Formatação
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Adiciona os handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Configuração dos loggers principais
LOGGERS: Dict[str, logging.Logger] = {}

def get_logger(name: str) -> logging.Logger:
    """Retorna um logger específico pelo nome"""
    if name not in LOGGERS:
        log_file = LOGS_DIR / f'{name}.log'
        LOGGERS[name] = setup_logger(name, log_file)
    return LOGGERS[name]

def set_console_log_level(level=logging.ERROR):
    """Define o nível de log para todos os handlers de console"""
    for logger_name, logger in LOGGERS.items():
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(level)
                
def set_file_log_level(level=logging.INFO):
    """Define o nível de log para todos os handlers de arquivo"""
    for logger_name, logger in LOGGERS.items():
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(level)

# Configuração inicial dos loggers
def initialize_logging():
    """Inicializa todos os loggers principais"""
    # Loggers padrão do sistema
    standard_loggers = ['app', 'database', 'migration', 'sync']
    
    for name in standard_loggers:
        if name not in LOGGERS:
            log_file = LOGS_DIR / f'{name}.log'
            LOGGERS[name] = setup_logger(name, log_file)
            LOGGERS[name].info(f"Inicializando logger: {name}")
    
    # Define o nível de log para o console como ERROR para reduzir a saída
    set_console_log_level(logging.ERROR) 
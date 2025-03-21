import logging.config
from .settings import LOG_CONFIG

# Inicializa a configuração de logging
logging.config.dictConfig(LOG_CONFIG)

# Logger para este módulo
logger = logging.getLogger(__name__)
logger.debug("Configurações de logging inicializadas")

# Inicialização do pacote config 

# Arquivo vazio para marcar o diretório como um módulo Python 
import logging
from pathlib import Path
from enum import Enum, auto
import os
import logging.config
from app.core.scripts.icon_mapper import IconMapper
import json
from datetime import datetime
import customtkinter as ctk
from typing import Callable, Any
import appdirs
import sys

# Informações da aplicação
APP_NAME = "Controlix"
APP_AUTHOR = "Controlix"
APP_VERSION = "1.0.0"

# Configuração de logging
logger = logging.getLogger(__name__)

# Determinar se estamos em modo de desenvolvimento ou produção
# Em desenvolvimento: __file__ é um arquivo .py
# Em produção (compilado): sys.frozen é definido pelo PyInstaller/cx_Freeze
IS_DEVELOPMENT = not getattr(sys, 'frozen', False)

# Diretório raiz do projeto
if IS_DEVELOPMENT:
    # Em desenvolvimento, usamos a estrutura de diretórios do projeto
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    
    # Diretórios principais da aplicação
    APP_DIR = ROOT_DIR / 'app'  # Diretório principal da aplicação
    CONFIG_DIR = APP_DIR / 'config'  # Configurações
    CORE_DIR = APP_DIR / 'core'  # Núcleo da aplicação
    DATA_DIR = APP_DIR / 'data'  # Dados e armazenamento
    UI_DIR = APP_DIR / 'ui'  # Interface do usuário
    
    # Diretórios de recursos
    BACKUP_DIR = ROOT_DIR / 'backups'  # Backups do sistema
    ICONS_DIR = ROOT_DIR / 'icons'  # Ícones e imagens
    IMAGES_DIR = ROOT_DIR / 'images'  # Imagens gerais
    LOGS_DIR = ROOT_DIR / 'logs'  # Arquivos de log
    
    # Diretório do banco de dados MySQL
    MYSQL_DIR = DATA_DIR / 'mysql'  # Banco MySQL e relacionados
else:
    # Em produção, usamos os diretórios específicos do sistema operacional
    USER_DATA_DIR = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    USER_CONFIG_DIR = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
    USER_CACHE_DIR = Path(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR))
    USER_LOG_DIR = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))
    
    # Definir diretórios principais
    ROOT_DIR = Path(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd())
    APP_DIR = ROOT_DIR
    CONFIG_DIR = USER_CONFIG_DIR
    DATA_DIR = USER_DATA_DIR
    UI_DIR = ROOT_DIR / 'ui'  # UI geralmente é empacotada com o executável
    
    # Diretórios de recursos
    BACKUP_DIR = USER_DATA_DIR / 'backups'
    ICONS_DIR = ROOT_DIR / 'icons'  # Ícones geralmente são empacotados com o executável
    IMAGES_DIR = ROOT_DIR / 'images'  # Imagens geralmente são empacotadas com o executável
    LOGS_DIR = USER_LOG_DIR
    
    # Diretório do banco de dados MySQL
    MYSQL_DIR = USER_DATA_DIR / 'mysql'

# Subdiretórios importantes
CACHE_DIR = DATA_DIR / 'cache' if IS_DEVELOPMENT else USER_CACHE_DIR
MIGRATIONS_DIR = DATA_DIR / 'migrations' if IS_DEVELOPMENT else USER_DATA_DIR / 'migrations'

# Diretórios de componentes principais
OBSERVER_DIR = CORE_DIR / 'observer'  # Padrão observer
SCRIPTS_DIR = CORE_DIR / 'scripts'  # Scripts utilitários
COMPONENTS_DIR = UI_DIR / 'components'  # Componentes da UI
WINDOWS_DIR = UI_DIR / 'windows'  # Janelas da aplicação
THEME_DIR = UI_DIR / 'theme'  # Temas e estilos

# Diretórios de segurança
SECURITY_DIR = ROOT_DIR / '.security' if IS_DEVELOPMENT else USER_DATA_DIR / '.security'
KEYS_DIR = SECURITY_DIR / 'keys'

# Diretórios MySQL
MYSQL_LOCAL_DIR = SECURITY_DIR / 'mysql_local'
MYSQL_REMOTE_DIR = SECURITY_DIR / 'mysql_remoto'

# Garante que os diretórios existam
for directory in [
    CONFIG_DIR, DATA_DIR, 
    BACKUP_DIR, ICONS_DIR, IMAGES_DIR, LOGS_DIR, MYSQL_DIR,
    CACHE_DIR, MIGRATIONS_DIR, SECURITY_DIR, KEYS_DIR,
    MYSQL_LOCAL_DIR, MYSQL_REMOTE_DIR
]:
    directory.mkdir(exist_ok=True, parents=True)

# Estrutura de diretórios do projeto
PROJECT_DIRS = {
    'root': ROOT_DIR,
    'app': {
        'path': APP_DIR,
        'subdirs': {
            'config': CONFIG_DIR,
            'core': CORE_DIR,
            'data': DATA_DIR,
            'ui': UI_DIR
        }
    },
    'data': {
        'path': DATA_DIR,
        'subdirs': {
            'mysql': MYSQL_DIR,
            'cache': CACHE_DIR,
            'migrations': MIGRATIONS_DIR
        }
    },
    'security': {
        'path': SECURITY_DIR,
        'subdirs': {
            'keys': KEYS_DIR,
            'mysql_local': MYSQL_LOCAL_DIR,
            'mysql_remote': MYSQL_REMOTE_DIR
        }
    },
    'logs': LOGS_DIR,
    'backups': BACKUP_DIR,
    'icons': ICONS_DIR,
    'images': IMAGES_DIR
}

# Aliases para compatibilidade e conveniência
CACHE_DIR = PROJECT_DIRS['data']['subdirs']['cache']
MIGRATION_DIR = PROJECT_DIRS['data']['subdirs']['migrations']

# Atualizar referências específicas
DATABASE = {
    'mysql': {
        'local': {
            'host': os.environ.get('MYSQL_LOCAL_HOST', 'localhost'),
            'port': int(os.environ.get('MYSQL_LOCAL_PORT', '3306')),
            'user': os.environ.get('MYSQL_LOCAL_USER', 'root'),
            'password': os.environ.get('MYSQL_LOCAL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_LOCAL_DATABASE', 'controlix_local')
        },
        'remote': {
            'host': os.environ.get('MYSQL_REMOTE_HOST', ''),
            'port': int(os.environ.get('MYSQL_REMOTE_PORT', '3306')),
            'user': os.environ.get('MYSQL_REMOTE_USER', ''),
            'password': os.environ.get('MYSQL_REMOTE_PASSWORD', ''),
            'database': os.environ.get('MYSQL_REMOTE_DATABASE', 'controlix_remote')
        }
    },
    'sync_settings': {
        'retry_interval': 300,  # segundos (5 minutos)
        'max_retries': 3,
        'batch_size': 1000,
        'tables_to_sync': [
            'users',
            'products',
            'customers',
            'orders'
        ],
        'priority_tables': [
            'users',
            'products'
        ]
    }
}

# Atualizar caminho do arquivo de configuração
CONFIG_FILE = PROJECT_DIRS['app']['subdirs']['data'] / 'user_settings.json'

# Garantir que os diretórios necessários existam
REQUIRED_DIRS = [
    PROJECT_DIRS['app']['path'],
    PROJECT_DIRS['data']['path'],
    PROJECT_DIRS['logs'],
    PROJECT_DIRS['backups'],
    PROJECT_DIRS['icons'],
    # Subdiretorios
    *PROJECT_DIRS['app']['subdirs'].values(),
    *PROJECT_DIRS['data']['subdirs'].values(),
    DATABASE['mysql']['local']['host'],
    MYSQL_DIR
]

for directory in REQUIRED_DIRS:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Carrega o mapeamento de ícones
icon_mapper = IconMapper(ICONS_DIR, ICONS_DIR / 'mapped')
try:
    icon_mapping_file = PROJECT_DIRS['app']['subdirs']['config'] / 'icon_mapping.json'
    
    # Se o arquivo não existe, faz o mapeamento inicial
    if not icon_mapping_file.exists():
        logger.info("Arquivo de mapeamento não encontrado, gerando...")
        icon_map = icon_mapper.scan_icons()
        icon_mapper.save_mapping(icon_mapping_file)
    else:
        icon_map = icon_mapper.load_mapping(icon_mapping_file)
    
    logger.debug(f"Mapeamento de ícones carregado com {len(icon_map)} ícones")
except Exception as e:
    logger.error(f"Erro ao carregar mapeamento de ícones: {e}")
    icon_map = {}

# Configurações de ícones
APP_ICONS = {
    'main': icon_mapper.get_icon_path('main'),
    'system': {
        'dark': icon_mapper.get_icon_path('logo_dark'),
        'light': icon_mapper.get_icon_path('logo_light')
    },
    'tray': {
        'default': icon_mapper.get_icon_path('coffee'),
        'info': icon_mapper.get_icon_path('info'),
        'warning': icon_mapper.get_icon_path('alert'),
        'error': icon_mapper.get_icon_path('error'),
        'success': icon_mapper.get_icon_path('success'),
    },
    'status': {
        'morning': icon_mapper.get_icon_path('morning'),
        'lunch': icon_mapper.get_icon_path('lunch-time'),
        'afternoon': icon_mapper.get_icon_path('afternoon'),
        'night': icon_mapper.get_icon_path('night'),
        'coffee': icon_mapper.get_icon_path('coffee'),
        'water': icon_mapper.get_icon_path('water')
    }
}

# Adicionar logs para debug
logger.debug("APP_ICONS mapeados:")
for category, icons in APP_ICONS.items():
    if isinstance(icons, dict):
        for name, path in icons.items():
            logger.debug(f"  {category}.{name}: {path}")
            logger.debug(f"  Existe: {Path(path).exists() if path else False}")
    else:
        logger.debug(f"  {category}: {icons}")
        logger.debug(f"  Existe: {Path(icons).exists() if icons else False}")

# Ícone padrão do aplicativo
DEFAULT_APP_ICON = APP_ICONS['main']

# Configurações de tema
class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

# Configurações da aplicação
APP_NAME = "Controlix"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("APP_DEBUG", "False").lower() == "true"

# Configurações de interface
WINDOW_SIZE = {
    'width': 800,
    'height': 600,
    'min_width': 640,
    'min_height': 480
}

# Configurações de tema
CURRENT_THEME = ThemeMode.SYSTEM
THEME_STYLES = {
    ThemeMode.LIGHT: {
        'fg_color': ['#DBDBDB', '#FFFFFF'],
        'text_color': ['#000000', '#000000'],
        'button': ['#3B8ED0', '#1F6AA5'],
        'button_hover': ['#36719F', '#144870'],
        'entry': ['#F9F9FA', '#F9F9FA'],
        'frame_low': ['#FFFFFF', '#FFFFFF'],
        'frame_high': ['#EBEBEB', '#EBEBEB'],
        'sidebar': ['#D1D5D8', '#D1D5D8'],
        'switch': ['#3B8ED0', '#1F6AA5'],
        'checkbox': ['#3B8ED0', '#1F6AA5'],
        'progressbar': ['#3B8ED0', '#1F6AA5'],
        'slider': ['#6B6B6B', '#26242F'],
        'border': ['#979DA2', '#979DA2'],
        'scrollbar': ['#4A4D50', '#4A4D50']
    },
    ThemeMode.DARK: {
        'fg_color': ['#2B2B2B', '#2B2B2B'],
        'text_color': ['#DCE4EE', '#DCE4EE'],
        'button': ['#3B8ED0', '#1F6AA5'],
        'button_hover': ['#36719F', '#144870'],
        'entry': ['#343638', '#343638'],
        'frame_low': ['#2B2B2B', '#2B2B2B'],
        'frame_high': ['#343638', '#343638'],
        'sidebar': ['#242424', '#242424'],
        'switch': ['#3B8ED0', '#1F6AA5'],
        'checkbox': ['#3B8ED0', '#1F6AA5'],
        'progressbar': ['#3B8ED0', '#1F6AA5'],
        'slider': ['#6B6B6B', '#26242F'],
        'border': ['#565B5E', '#565B5E'],
        'scrollbar': ['#4A4D50', '#4A4D50']
    }
}

# Configurações de cache de dados na memória
MAX_CACHE_SIZE_MB = 100

# Configurações de log
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        },
        'db_format': {
            'format': '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'verbose',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'db_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'db_format',
            'filename': LOGS_DIR / 'database.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'migration_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': LOGS_DIR / 'migration.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'sync_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': LOGS_DIR / 'sync.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        }
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'app_file'],
            'level': 'INFO',
            'propagate': True
        },
        'app': {  # Logger para toda a aplicação
            'handlers': ['app_file'],
            'level': 'INFO',
            'propagate': False
        },
        'app.data.connection': {  # Logger para conexões
            'handlers': ['db_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'app.data.mysql': {  # Logger específico para MySQL
            'handlers': ['db_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'app.data.cache': {  # Logger para cache
            'handlers': ['db_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'app.data.migrations': {  # Logger para migrações
            'handlers': ['migration_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'app.data.sync': {  # Logger para sincronização
            'handlers': ['sync_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'app.ui': {  # Logger para interface de usuário
            'handlers': ['console', 'app_file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

# Configurações de performance para limpeza de memória
CLEANUP_INTERVAL = 300000  # 5 minutos em milissegundos
MAX_MEMORY_USAGE_MB = 512

# Configurações de timeout
REQUEST_TIMEOUT = 30  # segundos
OPERATION_TIMEOUT = 60  # segundos

# Atualizar caminhos de segurança
CRYPTO_SETTINGS = {
    'key_file': PROJECT_DIRS['app']['subdirs']['data'] / 'key' / 'crypto.key',
    'env_file': ROOT_DIR / '.env.encrypted',
    'encoding': 'utf-8',
    'algorithm': 'AES-256-CBC',
    'key_length': 32,
    'salt_length': 16,
    'iterations': 100000
}

# Configurações de paginação e limites
PAGINATION = {
    'items_per_page': 50,
    'max_items_per_page': 100,
    'pagination_buttons': 5  # Número de botões visíveis no navegador de páginas
}

# Formatos de data e hora padrão
DATE_FORMATS = {
    'display': '%d/%m/%Y',
    'database': '%y-%m-%d',
    'datetime_display': '%d/%m/%Y %H:%M',
    'datetime_database': '%y-%m-%d %H:%M:%S',
    'time_display': '%H:%M',
    'time_database': '%H:%M:%S'
}

# Configurações de exportação
EXPORT_SETTINGS = {
    'formats': ['xlsx', 'csv', 'pdf'],
    'default_format': 'xlsx',
    'encoding': 'utf-8',
    'csv_separator': ';',
    'max_export_rows': 1000000
}

# Configurações de validação
VALIDATION = {
    'min_password_length': 8,
    'password_requires_special': True,
    'password_requires_numbers': True,
    'password_requires_uppercase': True,
    'max_login_attempts': 3,
    'lockout_duration_minutes': 30,
    'session_timeout_minutes': 60
}

# Configurações de arquivos
FILE_SETTINGS = {
    'max_upload_size_mb': 10,
    'allowed_extensions': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg'],
    'image_max_dimensions': {
        'width': 1920,
        'height': 1080
    },
    'thumbnail_size': {
        'width': 150,
        'height': 150
    }
}

# Configurações de mensagens e notificações
NOTIFICATION_SETTINGS = {
    'success_duration': 3000,  # milissegundos
    'error_duration': 5000,
    'warning_duration': 4000,
    'info_duration': 3000,
    'max_notifications': 5  # número máximo de notificações simultâneas
}

# Configurações de formatação de números
NUMBER_FORMATS = {
    'decimal_places': 2,
    'thousand_separator': '.',
    'decimal_separator': ',',
    'currency_symbol': 'R$',
    'currency_position': 'before'  # 'before' ou 'after'
}

# Estados brasileiros
ESTADOS_BR = [
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'),
    ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'),
    ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
    ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'),
    ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
]

# Status genéricos para uso em todo APP
STATUS_CHOICES = {
    'active': 'Ativo',
    'inactive': 'Inativo',
    'pending': 'Pendente',
    'cancelled': 'Cancelado',
    'completed': 'Concluído',
    'processing': 'Em Processamento',
    'error': 'Erro'
}

# Configurações de grid/tabela
GRID_SETTINGS = {
    'row_height': 40,
    'header_height': 45,
    'alternating_row_colors': True,
    'show_grid_lines': True,
    'selection_mode': 'single',  # 'single', 'multiple', 'none'
    'default_sort_direction': 'ascending'
}

# Configurações de horário comercial
BUSINESS_HOURS = {
    'start': '08:00',
    'interval_start': '12:00',
    'interval_end': '13:00',
    'end': '17:00'
}

# Feriados fixos anuais (formato: DD-MM)
HOLIDAYS = [
    '01-01',  # Ano Novo
    '21-04',  # Tiradentes
    '01-05',  # Dia do Trabalho
    '07-09',  # Independência
    '12-10',  # Nossa Senhora
    '02-11',  # Finados
    '15-11',  # Proclamação da República
    '25-12',  # Natal,
]

# Configurações de notificações
NOTIFICATIONS = {
    'enabled': True,
    'tray': {
        'enabled': True,
        'default_timeout': 10,
        'icon': APP_ICONS['tray']['default'],
        'levels': {
            'info': {
                'enabled': True,
                'icon': APP_ICONS['tray']['info'],
                'timeout': 5
            },
            'warning': {
                'enabled': True,
                'icon': APP_ICONS['tray']['warning'],
                'timeout': 15
            },
            'error': {
                'enabled': True,
                'icon': APP_ICONS['tray']['error'],
                'timeout': 30
            },
            'success': {
                'enabled': True,
                'icon': APP_ICONS['tray']['success'],
                'timeout': 5
            }
        },
        'business_notifications': {
            'start': {
                'enabled': True,
                'timeout': 5,
                'message': 'Início do Expediente',
                'icon': APP_ICONS['status']['morning']
            },
            'interval_start': {
                'enabled': True,
                'timeout': 5,
                'message': 'Hora do Almoço',
                'icon': APP_ICONS['status']['lunch']
            },
            'interval_end': {
                'enabled': True,
                'timeout': 5,
                'message': 'Retorno do Almoço',
                'icon': APP_ICONS['status']['afternoon']
            },
            'end': {
                'enabled': True,
                'timeout': 5,
                'message': 'Fim do Expediente',
                'icon': APP_ICONS['status']['night']
            },
            'coffee': {
                'enabled': True,
                'timeout': 5,
                'message': 'Hora do Café',
                'schedule': ['10:00', '15:00'],
                'icon': APP_ICONS['status']['coffee']
            },
            'water': {
                'enabled': True,
                'timeout': 5,
                'message': 'Hora de se Hidratar',
                'interval': 60,
                'icon': APP_ICONS['status']['water']
            }
        }
    },
    'messagebox': {
        'enabled': True,
        'levels': {
            'info': {
                'enabled': True,
                'icon': 'info'
            },
            'warning': {
                'enabled': True,
                'icon': 'warning'
            },
            'error': {
                'enabled': True,
                'icon': 'error'
            },
            'question': {
                'enabled': True,
                'icon': 'question'
            },
            'success': {
                'enabled': True,
                'icon': 'info'
            }
        }
    }
}

# Configurações de performance
PERFORMANCE_SETTINGS = {
    'cache_timeout': 300,        # Tempo em segundos antes do cache expirar
    'max_notifications_queue': 50,  # Número máximo de notificações na fila
    'cleanup_interval': 3600,    # Intervalo em segundos para limpeza de recursos
    'max_log_size': 10485760,   # Tamanho máximo dos arquivos de log (10MB)
    'memory_threshold': 512,     # Limite de uso de memória em MB
    'db_connection_timeout': 30, # Timeout para conexões de banco de dados
    'ui_update_interval': 1000,  # Intervalo de atualização da UI em milissegundos
    'cache_size': 100           # Tamanho máximo do cache em MB
}

# Configurações de janelas e monitores
WINDOW_SETTINGS = {
    'remember_positions': True,
    'center_on_screen': True,
    'preferred_monitor': 0,
    'appearance_mode': 'system',  # light, dark, system
    'color_theme': 'blue',       # blue, dark-blue, green
    'scaling_factor': 1.0,       # Escala da interface (1.0 = 100%)
    'windows': {}
}

# Configurações da janela de login
LOGIN_WINDOW_SETTINGS = {
    'size': {
        'width': 380,
        'height': 600,
        'min_width': 350,  # Tamanho mínimo para não quebrar o layout
        'min_height': 500  # Tamanho mínimo para mostrar todos os elementos
    },
    'style': {
        'title': {
            'font_size': 24,
            'font_weight': 'bold',
            'pady': 20,
            'color': '#FF8C00'  # Laranja
        },
        'entry': {
            'height': 35,
            'corner_radius': 5,
            'border_width': 1,
            'pady': 10
        },
        'button': {
            'height': 35,
            'corner_radius': 5,
            'border_width': 1,
            'font_weight': 'bold',
            'fg_color': '#FF8C00',  # Cor do botão
            'hover_color': '#E67E00'  # Cor quando hover
        }
    }
}

# Tema laranja personalizado
ORANGE_THEME = {
    "light": {
        "button": ["#FF8C00", "#FF6B00"],
        "button_hover": ["#E67E00", "#CC5500"],
        "text_color": ["#000000", "#000000"],
        "title_color": "#FF8C00"
    },
    "dark": {
        "button": ["#FF8C00", "#FF6B00"],
        "button_hover": ["#E67E00", "#CC5500"],
        "text_color": ["#FFFFFF", "#FFFFFF"],
        "title_color": "#FF8C00"
    }
}

# Garantir que os diretórios de log existam
os.makedirs(LOGS_DIR, exist_ok=True)

# Inicializar configuração de logging
logging.config.dictConfig(LOG_CONFIG)

try:
    logger.debug("Inicializando configurações...")
    logger.debug(f"ThemeMode definido: {[theme.value for theme in ThemeMode]}")
    logger.debug(f"BUSINESS_HOURS definido: {BUSINESS_HOURS}")
except Exception as e:
    logger.error(f"Erro ao inicializar configurações: {e}")
    raise

logger.debug("Configurações base carregadas")

# Garantir que o diretório de ícones existe e logar os arquivos encontrados
if not ICONS_DIR.exists():
    logger.error(f"Diretório de ícones não encontrado: {ICONS_DIR}")
else:
    logger.debug(f"Diretório de ícones encontrado: {ICONS_DIR}")
    logger.debug(f"Ícones disponíveis: {[f.name for f in ICONS_DIR.glob('*')]}")

class DynamicSettings:
    """Gerencia configurações dinâmicas do sistema."""
    
    def __init__(self):
        """Inicializa as configurações dinâmicas."""
        self.config_file = CONFIG_FILE
        self._settings = self._load_settings()
    
    def _load_settings(self) -> dict:
        """
        Carrega as configurações do arquivo.
        
        Returns:
            dict: Configurações carregadas.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Arquivo de configurações {self.config_file} não encontrado.")
                return {}
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return {}
    
    def save(self) -> None:
        """Salva as configurações no arquivo."""
        try:
            # Criar diretório pai se não existir
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
                
            logger.info("Configurações salvas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            raise
    
    def get_setting(self, path: list, default: Any = None) -> Any:
        """
        Obtém uma configuração pelo caminho.
        
        Args:
            path: Lista com o caminho para a configuração.
            default: Valor padrão se não encontrado.
            
        Returns:
            Any: Valor da configuração ou valor padrão.
        """
        current = self._settings
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def set_setting(self, path: list, value: Any) -> None:
        """
        Define uma configuração pelo caminho.
        
        Args:
            path: Lista com o caminho para a configuração.
            value: Valor a ser definido.
        """
        current = self._settings
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def delete_setting(self, path: list) -> None:
        """
        Remove uma configuração pelo caminho.
        
        Args:
            path: Lista com o caminho para a configuração.
        """
        current = self._settings
        for key in path[:-1]:
            if key not in current:
                return
            current = current[key]
        
        if path[-1] in current:
            del current[path[-1]]
    
    def clear(self) -> None:
        """Limpa todas as configurações."""
        self._settings.clear()
        self.save()

# Instância global das configurações dinâmicas
dynamic_settings = DynamicSettings()

SECURITY_SETTINGS = {
    'database_encryption': {
        'enabled': True,
        'algorithm': 'AES-256-CBC',
        'keys_dir': KEYS_DIR,  # Atualiza localização das chaves
        'key_length': 32,
        'iv_length': 16,
        'use_keyring': True,  # Usa o keyring do sistema quando disponível
        'keyring_service': APP_NAME,
        'keyring_username': 'database_key'
    }
}

# Configurações de backup
BACKUP_SETTINGS = {
    'auto_backup': {
        'enabled': True,
        'interval': 24,  # horas
        'keep_days': 30,  # dias para manter backups
        'types': ['full', 'incremental']
    },
    'backup_dir': BACKUP_DIR,
    'max_backups': 10
}

# Configurações de cache
CACHE_SETTINGS = {
    'max_size': 1000,           # Máximo de itens em cache
    'default_timeout': 300,     # 5 minutos em segundos
    'cleanup_interval': 3600,   # Limpeza a cada 1 hora
    'memory_warning': 75,       # Aviso em 75% de uso de memória
    'memory_critical': 90       # Limpeza em 90% de uso de memória
}

import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class IconMapper:
    def __init__(self, source_dir: Path, icons_dir: Path):
        """
        Inicializa o mapeador de ícones
        :param source_dir: Diretório onde os ícones estão localizados
        :param icons_dir: Diretório para o mapeamento
        """
        self.source_dir = Path(source_dir)
        self.icons_dir = Path(icons_dir)
        self.icon_map = {}
        
    def scan_icons(self) -> dict:
        """Escaneia os ícones disponíveis e retorna um mapeamento"""
        logger.debug(f"Escaneando ícones em: {self.source_dir}")
        
        # Extensões suportadas
        extensions = ('.ico', '.png', '.jpg', '.jpeg')
        
        try:
            # Escaneia arquivos
            for file in self.source_dir.glob('**/*'):
                if file.is_file() and file.suffix.lower() in extensions:
                    # Define o nome padronizado
                    icon_name = self._normalize_icon_name(file.stem)
                    # Adiciona ao mapeamento
                    self.icon_map[icon_name] = str(file)
            
            logger.info(f"Encontrados {len(self.icon_map)} ícones")
            return self.icon_map
            
        except Exception as e:
            logger.error(f"Erro ao escanear ícones: {e}")
            return {}
    
    def _normalize_icon_name(self, name: str) -> str:
        """Normaliza o nome do ícone para um formato padrão"""
        # Remove espaços e caracteres especiais
        name = name.lower().replace(' ', '_')
        # Remove extensão se presente
        name = name.split('.')[0]
        return name
    
    def save_mapping(self, output_file: Path):
        """Salva o mapeamento em um arquivo JSON"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.icon_map, f, indent=4)
            logger.info(f"Mapeamento salvo em: {output_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar mapeamento: {e}")
    
    def load_mapping(self, input_file: Path) -> dict:
        """Carrega o mapeamento de um arquivo JSON"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                self.icon_map = json.load(f)
            logger.info(f"Mapeamento carregado de: {input_file}")
            return self.icon_map
        except Exception as e:
            logger.error(f"Erro ao carregar mapeamento: {e}")
            return {}
    
    def get_icon_path(self, icon_name: str) -> str:
        """Retorna o caminho completo para um ícone"""
        normalized_name = self._normalize_icon_name(icon_name)
        return self.icon_map.get(normalized_name, '')
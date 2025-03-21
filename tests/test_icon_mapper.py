import sys
from pathlib import Path
import logging

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from app.core.scripts.icon_mapper import IconMapper

# Configura logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_mapping():
    """Testa o mapeamento de ícones"""
    try:
        # Define diretórios para teste
        source_dir = root_dir / 'icons'
        icons_dir = root_dir / 'icons' / 'mapped'
        output_file = root_dir / 'config' / 'icon_mapping.json'
        
        # Cria o mapeador
        mapper = IconMapper(source_dir, icons_dir)
        
        # Executa o mapeamento
        icon_map = mapper.scan_icons()
        
        # Mostra resultados
        logger.info("Ícones encontrados:")
        for name, path in icon_map.items():
            logger.info(f"  {name}: {path}")
        
        # Salva o mapeamento
        mapper.save_mapping(output_file)
        
        # Testa carregamento
        new_mapper = IconMapper(source_dir, icons_dir)
        loaded_map = new_mapper.load_mapping(output_file)
        
        assert icon_map == loaded_map, "Mapeamento carregado difere do original"
        logger.info("Teste concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    test_mapping() 
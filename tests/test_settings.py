import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import json
from app.config.settings import DynamicSettings, ThemeMode

class TestDynamicSettings(unittest.TestCase):
    def setUp(self):
        """Configura o ambiente de teste"""
        # Usa o diretório de teste para não interferir nas configurações reais
        self.test_dir = Path(__file__).parent / 'test_data'
        self.test_dir.mkdir(exist_ok=True)
        self.test_config_file = self.test_dir / 'test_settings.json'
        
        # Cria configurações iniciais de teste
        self.initial_settings = {
            "window": {
                "appearance_mode": "system",
                "color_theme": "blue",
                "scaling_factor": 1.0
            }
        }
        
        # Salva as configurações iniciais
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            json.dump(self.initial_settings, f, indent=4)
        
        # Cria uma instância de DynamicSettings específica para teste
        self.settings = DynamicSettings()
        # Sobrescreve o arquivo de configuração para usar o arquivo de teste
        self.settings.config_file = self.test_config_file
        # Recarrega as configurações do arquivo de teste
        self.settings._settings = self.settings._load_settings()
    
    def tearDown(self):
        """Limpa o ambiente após os testes"""
        try:
            if self.test_config_file.exists():
                self.test_config_file.unlink()  # Remove o arquivo de teste
            if self.test_dir.exists():
                self.test_dir.rmdir()  # Remove o diretório de teste
        except Exception as e:
            print(f"Erro ao limpar ambiente de teste: {e}")
    
    def test_save_and_load_settings(self):
        """Testa se as configurações são salvas e carregadas corretamente"""
        # Define um tema
        self.settings.set_window_setting('appearance_mode', 'dark')
        
        # Verifica se foi salvo
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)
        
        self.assertEqual(
            saved_settings['window']['appearance_mode'],
            'dark',
            "O tema não foi salvo corretamente no arquivo"
        )
        
        # Muda para outro tema
        self.settings.set_window_setting('appearance_mode', 'light')
        
        # Verifica se foi atualizado
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            updated_settings = json.load(f)
        
        self.assertEqual(
            updated_settings['window']['appearance_mode'],
            'light',
            "O tema não foi atualizado corretamente no arquivo"
        )

    def test_color_theme_setting(self):
        """Testa se as configurações de tema de cores são salvas corretamente"""
        # Define um tema de cores
        self.settings.set_window_setting('color_theme', 'dark-blue')
        
        # Verifica se foi salvo
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)
        
        self.assertEqual(
            saved_settings['window']['color_theme'],
            'dark-blue',
            "O tema de cores não foi salvo corretamente"
        )

if __name__ == '__main__':
    unittest.main() 
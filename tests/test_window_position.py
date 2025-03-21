import unittest
from pathlib import Path
import json
from app.config.settings import DynamicSettings
import customtkinter as ctk
from app.core.scripts.window_position_mixin import WindowPositionMixin
from unittest.mock import patch

class TestWindow(WindowPositionMixin, ctk.CTk):
    def __init__(self, settings=None):
        super().__init__()
        self.geometry("300x200")
        self.settings = settings
        self.setup_window_position('test_window')

class TestWindowPosition(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).parent / 'test_data'
        self.test_dir.mkdir(exist_ok=True)
        self.test_config_file = self.test_dir / 'test_settings.json'
        
        # Configurações iniciais
        self.initial_settings = {"window": {"remember_positions": True, "windows": {}}}
        with open(self.test_config_file, 'w') as f:
            json.dump(self.initial_settings, f)
            
        self.settings = DynamicSettings()
        self.settings.config_file = self.test_config_file
    
    def test_window_position_save(self):
        with patch('app.core.scripts.window_position_mixin.dynamic_settings', self.settings):
            window = TestWindow()
            window.geometry("300x200+100+100")
            window._save_current_position()
            
            with open(self.test_config_file, 'r') as f:
                saved_settings = json.load(f)
            
            self.assertIn('windows', saved_settings['window'])
            self.assertIn('test_window', saved_settings['window']['windows'])
            
            position = saved_settings['window']['windows']['test_window']['position']
            self.assertTrue(isinstance(position, list), "A posição deve ser uma lista")
            self.assertEqual(len(position), 2, "A posição deve ter 2 elementos")
            
            size = saved_settings['window']['windows']['test_window']['size']
            self.assertTrue(isinstance(size, list), "O tamanho deve ser uma lista")
            self.assertEqual(len(size), 2, "O tamanho deve ter 2 elementos")
            
            self.assertTrue(all(isinstance(x, int) and x > 0 for x in position), 
                           "Posição deve conter inteiros positivos")
            self.assertTrue(all(isinstance(x, int) and x > 0 for x in size), 
                           "Tamanho deve conter inteiros positivos")

if __name__ == '__main__':
    unittest.main() 
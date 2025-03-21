import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from app.ui.theme.theme_manager import theme_manager
from app.config.settings import ThemeMode

class ThemeTester(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Teste de Temas")
        self.geometry("800x600")
        
        # Inicializa o gerenciador de temas
        theme_manager.initialize()
        
        # Cria os widgets de teste
        self._create_widgets()
        
    def _create_widgets(self):
        # Frame principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Teste de Temas",
            font=("Arial", 24, "bold")
        )
        self.title_label.pack(pady=20)
        
        # Frame para botões de tema
        self.theme_frame = ctk.CTkFrame(self.main_frame)
        self.theme_frame.pack(pady=20)
        
        # Botões de tema
        self.light_button = ctk.CTkButton(
            self.theme_frame,
            text="Tema Claro",
            command=lambda: theme_manager.set_theme(ThemeMode.LIGHT)
        )
        self.light_button.pack(side="left", padx=10)
        
        self.dark_button = ctk.CTkButton(
            self.theme_frame,
            text="Tema Escuro",
            command=lambda: theme_manager.set_theme(ThemeMode.DARK)
        )
        self.dark_button.pack(side="left", padx=10)
        
        self.system_button = ctk.CTkButton(
            self.theme_frame,
            text="Tema do Sistema",
            command=lambda: theme_manager.set_theme(ThemeMode.SYSTEM)
        )
        self.system_button.pack(side="left", padx=10)
        
        self.toggle_button = ctk.CTkButton(
            self.theme_frame,
            text="Alternar Tema",
            command=theme_manager.toggle_theme
        )
        self.toggle_button.pack(side="left", padx=10)
        
        # Frame para elementos de UI
        self.ui_frame = ctk.CTkFrame(self.main_frame)
        self.ui_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Exemplos de widgets
        # Entry
        self.test_entry = ctk.CTkEntry(
            self.ui_frame,
            placeholder_text="Campo de texto exemplo"
        )
        self.test_entry.pack(pady=10, fill="x")
        
        # Text area
        self.test_textbox = ctk.CTkTextbox(
            self.ui_frame,
            height=100
        )
        self.test_textbox.pack(pady=10, fill="x")
        self.test_textbox.insert("1.0", "Área de texto exemplo\nCom múltiplas linhas")
        
        # Checkbox
        self.test_checkbox = ctk.CTkCheckBox(
            self.ui_frame,
            text="Checkbox exemplo"
        )
        self.test_checkbox.pack(pady=10)
        
        # Radio buttons
        self.radio_var = ctk.StringVar(value="opcao1")
        self.test_radio1 = ctk.CTkRadioButton(
            self.ui_frame,
            text="Opção 1",
            variable=self.radio_var,
            value="opcao1"
        )
        self.test_radio1.pack(pady=5)
        
        self.test_radio2 = ctk.CTkRadioButton(
            self.ui_frame,
            text="Opção 2",
            variable=self.radio_var,
            value="opcao2"
        )
        self.test_radio2.pack(pady=5)
        
        # Progress bar
        self.test_progress = ctk.CTkProgressBar(self.ui_frame)
        self.test_progress.pack(pady=10, fill="x")
        self.test_progress.set(0.7)
        
        # Slider
        self.test_slider = ctk.CTkSlider(
            self.ui_frame,
            from_=0,
            to=100,
            number_of_steps=10
        )
        self.test_slider.pack(pady=10, fill="x")
        self.test_slider.set(30)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text=f"Tema atual: {theme_manager.current_theme.value}"
        )
        self.status_label.pack(pady=10)
        
        # Observa mudanças de tema
        theme_manager.add_observer(self._update_status)
    
    def _update_status(self):
        """Atualiza o label de status quando o tema muda"""
        self.status_label.configure(text=f"Tema atual: {theme_manager.current_theme.value}")

def main():
    app = ThemeTester()
    app.mainloop()

if __name__ == "__main__":
    main() 
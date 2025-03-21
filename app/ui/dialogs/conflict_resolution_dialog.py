import customtkinter as ctk
from tkinter import messagebox
import json
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConflictResolutionDialog(ctk.CTkToplevel):
    """
    Diálogo para resolução de conflitos de sincronização entre MySQL local e remoto.
    Permite visualizar as diferenças e escolher qual versão manter.
    """
    
    def __init__(self, parent, conflict: Dict[str, Any], callback: Callable[[Dict[str, Any], str], None]):
        """
        Inicializa o diálogo de resolução de conflitos.
        
        Args:
            parent: Widget pai
            conflict: Dicionário com informações do conflito
            callback: Função a ser chamada quando o conflito for resolvido
        """
        super().__init__(parent)
        
        self.parent = parent
        self.conflict = conflict
        self.callback = callback
        self.resolution_type = ctk.StringVar(value="local")
        
        # Configurações da janela
        self.title("Resolução de Conflito")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        # Criar widgets
        self._create_widgets()
        
        # Preencher dados
        self._populate_data(conflict)
        
        # Tornar modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        
        # Centralizar na tela
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """Cria os widgets do diálogo"""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Informações do conflito
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        conflict_label = ctk.CTkLabel(
            info_frame, 
            text="Conflito detectado na sincronização. Escolha qual versão manter:",
            font=("Roboto", 14, "bold")
        )
        conflict_label.pack(pady=10)
        
        # Detalhes do conflito
        details_frame = ctk.CTkFrame(info_frame)
        details_frame.pack(fill="x", padx=10, pady=5)
        
        self.table_label = ctk.CTkLabel(details_frame, text="Tabela: ")
        self.table_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.id_label = ctk.CTkLabel(details_frame, text="ID: ")
        self.id_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        # Frame de comparação
        self.comparison_frame = ctk.CTkFrame(main_frame)
        self.comparison_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configurar grid para comparação
        self.comparison_frame.columnconfigure(0, weight=1)
        self.comparison_frame.columnconfigure(1, weight=1)
        self.comparison_frame.rowconfigure(1, weight=1)
        
        # Títulos
        self.local_title = ctk.CTkLabel(
            self.comparison_frame,
            text="Versão Local",
            font=("Roboto", 12, "bold")
        )
        self.local_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.remote_title = ctk.CTkLabel(
            self.comparison_frame,
            text="Versão Remota",
            font=("Roboto", 12, "bold")
        )
        self.remote_title.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Áreas de texto para os dados
        self.local_data_text = ctk.CTkTextbox(self.comparison_frame, wrap="word")
        self.local_data_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        self.remote_data_text = ctk.CTkTextbox(self.comparison_frame, wrap="word")
        self.remote_data_text.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")
        
        # Frame para opções de resolução
        resolution_frame = ctk.CTkFrame(main_frame)
        resolution_frame.pack(fill="x", padx=10, pady=10)
        
        resolution_label = ctk.CTkLabel(
            resolution_frame,
            text="Escolha a resolução:",
            font=("Roboto", 12, "bold")
        )
        resolution_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Opções de resolução
        self.local_radio = ctk.CTkRadioButton(
            resolution_frame,
            text="Usar versão Local",
            variable=self.resolution_type,
            value="local"
        )
        self.local_radio.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        self.remote_radio = ctk.CTkRadioButton(
            resolution_frame,
            text="Usar versão Remota",
            variable=self.resolution_type,
            value="remote"
        )
        self.remote_radio.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.newest_radio = ctk.CTkRadioButton(
            resolution_frame,
            text="Usar versão mais recente",
            variable=self.resolution_type,
            value="newest"
        )
        self.newest_radio.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        self.manual_radio = ctk.CTkRadioButton(
            resolution_frame,
            text="Editar manualmente",
            variable=self.resolution_type,
            value="manual"
        )
        self.manual_radio.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        # Botões de ação
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.resolve_button = ctk.CTkButton(
            button_frame,
            text="Resolver Conflito",
            command=self._resolve_conflict
        )
        self.resolve_button.pack(side="right", padx=10, pady=10)
        
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancelar",
            fg_color="gray",
            command=self.destroy
        )
        self.cancel_button.pack(side="right", padx=10, pady=10)
    
    def _populate_data(self, conflict: Dict[str, Any]):
        """
        Preenche os dados do conflito nos widgets.
        
        Args:
            conflict: Dicionário com informações do conflito
        """
        # Informações básicas
        table_name = conflict.get('table', 'Desconhecida')
        record_id = conflict.get('record_id', 'Desconhecido')
        
        self.table_label.configure(text=f"Tabela: {table_name}")
        self.id_label.configure(text=f"ID: {record_id}")
        
        # Limpar áreas de texto
        self.local_data_text.delete("0.0", "end")
        self.remote_data_text.delete("0.0", "end")
        
        # Dados
        local_data = conflict.get('local_data', {})
        remote_data = conflict.get('remote_data', {})
        
        # Formatar como JSON para melhor visualização
        local_formatted = json.dumps(local_data, indent=2, ensure_ascii=False)
        remote_formatted = json.dumps(remote_data, indent=2, ensure_ascii=False)
        
        # Inserir nos campos de texto
        self.local_data_text.insert("0.0", local_formatted)
        self.remote_data_text.insert("0.0", remote_formatted)
        
        # Destacar diferenças
        self._highlight_differences(local_data, remote_data)
        
        # Pré-selecionar a opção mais adequada
        self._preselect_resolution(conflict)
    
    def _highlight_differences(self, local_data: Dict, remote_data: Dict):
        """Destaca as diferenças entre os dados local e remoto"""
        try:
            # Encontrar diferenças
            differences = []
            
            # Comparar todos os campos
            for key in set(local_data.keys()) | set(remote_data.keys()):
                if key not in local_data:
                    differences.append(key)
                elif key not in remote_data:
                    differences.append(key)
                elif local_data[key] != remote_data[key]:
                    differences.append(key)
            
            # Destacar diferenças nos campos de texto
            for key in differences:
                # Destacar no texto local
                if key in local_data:
                    self._highlight_key_in_text(self.local_data_text, key)
                
                # Destacar no texto remoto
                if key in remote_data:
                    self._highlight_key_in_text(self.remote_data_text, key)
                    
        except Exception as e:
            logger.error(f"Erro ao destacar diferenças: {e}")
    
    def _highlight_key_in_text(self, text_widget, key):
        """Destaca uma chave específica em um widget de texto"""
        try:
            # Encontrar a chave no texto
            content = text_widget.get("0.0", "end")
            start_index = content.find(f'"{key}"')
            
            if start_index >= 0:
                # Converter índice para linha.coluna
                line_count = content[:start_index].count('\n')
                col_count = start_index - content[:start_index].rfind('\n') - 1
                
                # Ajustar para formato tkinter (1-based para linhas)
                start_pos = f"{line_count + 1}.{col_count}"
                
                # Encontrar o final da linha
                end_line = content[start_index:].find('\n')
                if end_line < 0:
                    end_line = len(content[start_index:])
                
                end_pos = f"{line_count + 1}.{col_count + end_line}"
                
                # Aplicar tag de destaque
                text_widget.tag_add("highlight", start_pos, end_pos)
                text_widget.tag_configure("highlight", background="yellow")
                
        except Exception as e:
            logger.error(f"Erro ao destacar chave no texto: {e}")
    
    def _preselect_resolution(self, conflict: Dict[str, Any]):
        """Pré-seleciona a opção de resolução mais adequada com base nos dados do conflito"""
        try:
            # Verificar versões
            local_data = conflict.get('local_data', {})
            remote_data = conflict.get('remote_data', {})
            
            local_version = conflict.get('local_version', 1)
            remote_version = conflict.get('remote_version', 1)
            
            # Se as versões são diferentes, usar a mais recente
            if local_version != remote_version:
                self.resolution_type.set("newest")
                return
                
            # Verificar timestamps de modificação
            local_modified = conflict.get('local_modified', '')
            remote_modified = conflict.get('remote_modified', '')
            
            if local_modified and remote_modified and local_modified != remote_modified:
                self.resolution_type.set("newest")
                return
                
            # Padrão: usar versão local
            self.resolution_type.set("local")
            
        except Exception as e:
            logger.error(f"Erro ao pré-selecionar resolução: {e}")
            self.resolution_type.set("local")  # Fallback para local
    
    def _resolve_conflict(self):
        """Resolve o conflito com base na opção selecionada"""
        try:
            resolution_type = self.resolution_type.get()
            conflict = self.conflict
            
            # Obter dados
            local_data = conflict.get('local_data', {})
            remote_data = conflict.get('remote_data', {})
            
            # Determinar dados resolvidos com base na escolha
            resolved_data = {}
            
            if resolution_type == 'local':
                # Usa versão local
                resolved_data = local_data.copy()
            elif resolution_type == 'remote':
                # Usa versão remota
                resolved_data = remote_data.copy()
            elif resolution_type == 'newest':
                # Usa a versão mais recente
                local_version = conflict.get('local_version', 1)
                remote_version = conflict.get('remote_version', 1)
                
                if local_version > remote_version:
                    # Local tem versão mais recente
                    resolved_data = local_data.copy()
                elif remote_version > local_version:
                    # Remoto tem versão mais recente
                    resolved_data = remote_data.copy()
                else:
                    # Versões iguais, verificar timestamp
                    local_modified = conflict.get('local_modified', '')
                    remote_modified = conflict.get('remote_modified', '')
                    
                    if local_modified > remote_modified:
                        # Local tem modificação mais recente
                        resolved_data = local_data.copy()
                    else:
                        # Remoto tem modificação mais recente ou igual
                        resolved_data = remote_data.copy()
            elif resolution_type == 'manual':
                # Edição manual - abrir diálogo de edição
                self._open_manual_editor()
                return
            
            # Chamar callback com a resolução
            self.callback(resolved_data, resolution_type)
            
            # Fechar diálogo
            self.destroy()
            
        except Exception as e:
            logger.error(f"Erro ao resolver conflito: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro ao resolver o conflito: {e}")
    
    def _open_manual_editor(self):
        """Abre um editor para edição manual dos dados"""
        try:
            # Criar diálogo de edição
            editor_dialog = ManualResolutionDialog(self, self.conflict, self._handle_manual_resolution)
            
        except Exception as e:
            logger.error(f"Erro ao abrir editor manual: {e}")
            messagebox.showerror("Erro", f"Não foi possível abrir o editor manual: {e}")
    
    def _handle_manual_resolution(self, resolved_data: Dict[str, Any]):
        """
        Manipula a resolução manual do conflito.
        
        Args:
            resolved_data: Dados resolvidos manualmente
        """
        try:
            # Chamar callback com a resolução
            self.callback(resolved_data, "manual")
            
            # Fechar diálogo
            self.destroy()
            
        except Exception as e:
            logger.error(f"Erro ao processar resolução manual: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro ao processar a resolução manual: {e}")


class ManualResolutionDialog(ctk.CTkToplevel):
    """Diálogo para edição manual de dados para resolução de conflitos"""
    
    def __init__(self, parent, conflict: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]):
        """
        Inicializa o diálogo de edição manual.
        
        Args:
            parent: Widget pai
            conflict: Dicionário com informações do conflito
            callback: Função a ser chamada quando a edição for concluída
        """
        super().__init__(parent)
        
        self.parent = parent
        self.conflict = conflict
        self.callback = callback
        
        # Configurações da janela
        self.title("Edição Manual")
        self.geometry("600x500")
        self.minsize(500, 400)
        
        # Criar widgets
        self._create_widgets()
        
        # Preencher dados
        self._populate_data(conflict)
        
        # Tornar modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        
        # Centralizar na tela
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """Cria os widgets do diálogo"""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Instruções
        instructions = ctk.CTkLabel(
            main_frame,
            text="Edite os dados manualmente para resolver o conflito:",
            font=("Roboto", 12, "bold")
        )
        instructions.pack(pady=10)
        
        # Área de texto para edição
        self.editor = ctk.CTkTextbox(main_frame, wrap="word")
        self.editor.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botões
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.save_button = ctk.CTkButton(
            button_frame,
            text="Salvar",
            command=self._save_changes
        )
        self.save_button.pack(side="right", padx=10, pady=10)
        
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancelar",
            fg_color="gray",
            command=self.destroy
        )
        self.cancel_button.pack(side="right", padx=10, pady=10)
    
    def _populate_data(self, conflict: Dict[str, Any]):
        """
        Preenche os dados do conflito no editor.
        
        Args:
            conflict: Dicionário com informações do conflito
        """
        # Limpar editor
        self.editor.delete("0.0", "end")
        
        # Mesclar dados para edição
        merged_data = {}
        
        # Adicionar todos os campos de ambas as versões
        local_data = conflict.get('local_data', {})
        remote_data = conflict.get('remote_data', {})
        
        # Primeiro, adicionar todos os campos da versão local
        merged_data.update(local_data)
        
        # Depois, adicionar campos da versão remota que não existem na local
        for key, value in remote_data.items():
            if key not in merged_data:
                merged_data[key] = value
        
        # Formatar como JSON para edição
        formatted_data = json.dumps(merged_data, indent=2, ensure_ascii=False)
        
        # Inserir no editor
        self.editor.insert("0.0", formatted_data)
    
    def _save_changes(self):
        """Salva as alterações feitas manualmente"""
        try:
            # Obter texto editado
            edited_text = self.editor.get("0.0", "end").strip()
            
            # Converter de volta para dicionário
            resolved_data = json.loads(edited_text)
            
            # Chamar callback com os dados resolvidos
            self.callback(resolved_data)
            
            # Fechar diálogo
            self.destroy()
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Erro de Formato", f"O JSON editado contém erros: {e}")
        except Exception as e:
            logger.error(f"Erro ao salvar alterações manuais: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro ao salvar as alterações: {e}") 
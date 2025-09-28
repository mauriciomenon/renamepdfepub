#!/usr/bin/env python3
"""
Limpador de Arquivos MD
=====================

Remove emojis e caracteres especiais dos arquivos Markdown
conforme solicitado pelo usuario.
"""

import re
import unicodedata
from pathlib import Path
from typing import List

class MDCleaner:
    """Limpa arquivos Markdown removendo emojis e caracteres especiais"""
    
    def __init__(self):
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
    
    def clean_text(self, text: str) -> str:
        """Remove emojis e normaliza caracteres especiais"""
        if not text:
            return text
        
        # Remove emojis
        text = self.emoji_pattern.sub('', text)
        
        # Remove acentos (NFD + remove combining characters)
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove outros caracteres especiais, mas preserva Markdown
        # Mantem: # * _ ` [ ] ( ) - = + | : ; " ' , . ! ? 
        text = re.sub(r'[^\w\s#*_`\[\]()=+|:;"\',.!?\-]', '', text)
        
        # Normaliza espacos multiplos
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 line breaks
        text = re.sub(r'[ \t]+', ' ', text)  # Normaliza espacos
        
        return text
    
    def clean_md_file(self, file_path: Path) -> bool:
        """Limpa um arquivo MD individual"""
        try:
            # Le conteudo original
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Limpa conteudo
            cleaned_content = self.clean_text(original_content)
            
            # Verifica se houve mudancas
            if original_content != cleaned_content:
                # Cria backup
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Salva versao limpa
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                print(f"Limpo: {file_path.name} (backup criado)")
                return True
            else:
                print(f"Sem mudancas: {file_path.name}")
                return False
        
        except Exception as e:
            print(f"Erro processando {file_path.name}: {e}")
            return False
    
    def find_md_files(self) -> List[Path]:
        """Encontra todos os arquivos .md no diretorio"""
        current_dir = Path(".")
        md_files = list(current_dir.glob("*.md"))
        return sorted(md_files)
    
    def clean_all_md_files(self) -> None:
        """Limpa todos os arquivos MD encontrados"""
        md_files = self.find_md_files()
        
        if not md_files:
            print("Nenhum arquivo .md encontrado")
            return
        
        print(f"LIMPEZA DE ARQUIVOS MD")
        print(f"=====================")
        print(f"Encontrados {len(md_files)} arquivos .md")
        print()
        
        cleaned_count = 0
        
        for md_file in md_files:
            if self.clean_md_file(md_file):
                cleaned_count += 1
        
        print()
        print(f"RESUMO:")
        print(f"- Arquivos processados: {len(md_files)}")
        print(f"- Arquivos modificados: {cleaned_count}")
        print(f"- Backups criados: {cleaned_count}")
        print()
        print("Limpeza concluida!")

def main():
    """Funcao principal"""
    cleaner = MDCleaner()
    cleaner.clean_all_md_files()

if __name__ == "__main__":
    main()
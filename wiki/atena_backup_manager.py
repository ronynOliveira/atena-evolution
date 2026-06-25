# nome do arquivo: atena_backup_manager.py
"""
Gerenciador de Backup da Atena - Orquestra o backup de dados do usuário para o Google Drive.
"""
import os
import logging
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime

from google_drive_agent import GoogleDriveAgent

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, user_memory_path: str = "memoria_do_usuario/"):
        self.user_memory_path = Path(user_memory_path)
        self.google_drive_agent = GoogleDriveAgent()
        self.backup_folder_name = "Backup_Atena"
        self.backup_folder_id = None
        logger.info("BackupManager inicializado.")

    async def _get_or_create_backup_folder(self) -> Optional[str]:
        """Verifica se a pasta de backup existe no Google Drive, senão a cria."""
        if not self.google_drive_agent.drive_service:
            logger.error("Serviço do Google Drive não disponível. Não é possível gerenciar pastas.")
            return None

        # Tenta encontrar a pasta
        files = self.google_drive_agent.list_files(page_size=100) # Aumenta o page_size para buscar mais pastas
        for file in files:
            if file.get('name') == self.backup_folder_name and file.get('mimeType') == 'application/vnd.google-apps.folder':
                self.backup_folder_id = file['id']
                logger.info(f"Pasta de backup '{self.backup_folder_name}' encontrada com ID: {self.backup_folder_id}")
                return self.backup_folder_id

        # Se não encontrou, cria a pasta
        logger.info(f"Pasta de backup '{self.backup_folder_name}' não encontrada. Criando...")
        file_metadata = {
            'name': self.backup_folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        try:
            folder = self.google_drive_agent.drive_service.files().create(body=file_metadata, fields='id').execute()
            self.backup_folder_id = folder.get('id')
            logger.info(f"Pasta '{self.backup_folder_name}' criada com ID: {self.backup_folder_id}")
            return self.backup_folder_id
        except Exception as e:
            logger.error(f"Erro ao criar pasta de backup no Google Drive: {e}")
            return None

    async def run_backup(self):
        """Executa o processo de backup dos arquivos da memória do usuário para o Google Drive."""
        logger.info("Iniciando processo de backup...")
        if not self.google_drive_agent.drive_service:
            logger.warning("Backup não pode ser executado: Serviço do Google Drive não disponível.")
            return

        if not self.user_memory_path.is_dir():
            logger.error(f"Caminho da memória do usuário não encontrado: {self.user_memory_path}")
            return

        self.backup_folder_id = await self._get_or_create_backup_folder()
        if not self.backup_folder_id:
            logger.error("Não foi possível obter ou criar a pasta de backup no Google Drive. Backup abortado.")
            return

        for file_path in self.user_memory_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'): # Ignora arquivos ocultos
                await self._upload_file_to_drive(file_path)
        
        logger.info("Processo de backup concluído.")

    async def _upload_file_to_drive(self, local_file_path: Path):
        """Faz o upload de um arquivo local para o Google Drive, atualizando se já existir."""
        file_name = local_file_path.name
        logger.info(f"Processando arquivo para backup: {file_name}")

        # Verifica se o arquivo já existe no Drive
        existing_files = self.google_drive_agent.list_files(folder_id=self.backup_folder_id, page_size=100)
        file_id_to_update = None
        for f in existing_files:
            if f.get('name') == file_name:
                file_id_to_update = f['id']
                break

        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(local_file_path, resumable=True)

        if file_id_to_update:
            # Atualiza arquivo existente
            try:
                updated_file = self.google_drive_agent.drive_service.files().update(
                    fileId=file_id_to_update,
                    media_body=media
                ).execute()
                logger.info(f"Arquivo '{file_name}' atualizado no Google Drive. ID: {updated_file.get('id')}")
            except Exception as e:
                logger.error(f"Erro ao atualizar arquivo '{file_name}' no Google Drive: {e}")
        else:
            # Faz upload de novo arquivo
            file_metadata = {
                'name': file_name,
                'parents': [self.backup_folder_id]
            }
            try:
                uploaded_file = self.google_drive_agent.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"Arquivo '{file_name}' enviado para o Google Drive. ID: {uploaded_file.get('id')}")
            except Exception as e:
                logger.error(f"Erro ao enviar arquivo '{file_name}' para o Google Drive: {e}")

# Exemplo de uso (para testes)
async def main():
    print("--- Teste do BackupManager da Atena ---")
    # Certifique-se de que credentials.json e token.pickle estão configurados
    # e que a pasta memoria_do_usuario existe com alguns arquivos.
    
    # Crie alguns arquivos dummy para teste
    Path("memoria_do_usuario").mkdir(exist_ok=True)
    with open("memoria_do_usuario/teste_lexico.json", "w") as f:
        f.write('{"ola": {"transcricao_crua": "ola", "texto_confirmado": "olá"}}')
    with open("memoria_do_usuario/teste_perfil.json", "w") as f:
        f.write('{"nome": "Teste", "idade": 30}')

    backup_manager = BackupManager(user_memory_path="memoria_do_usuario")
    await backup_manager.run_backup()
    print("--- Teste concluído ---")

if __name__ == "__main__":
    asyncio.run(main())

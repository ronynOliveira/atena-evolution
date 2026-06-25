# nome do arquivo: google_drive_agent.py
"""
Módulo de Agente para interagir com a API do Google Drive e Google Docs.
Permite à Atena ler, criar e gerenciar arquivos no Google Drive do usuário.
"""
import os
import pickle
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Optional, Dict

# Configuração
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

logger = logging.getLogger(__name__)

class GoogleDriveAgent:
    def __init__(self):
        """Inicializa o agente e lida com a autenticação."""
        self.creds = self._get_credentials()
        try:
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.docs_service = build('docs', 'v1', credentials=self.creds)
            logger.info("Agente do Google Drive conectado com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao construir os serviços do Google: {e}")
            self.drive_service = None
            self.docs_service = None

    def _get_credentials(self) -> Optional[Credentials]:
        """
        Obtém as credenciais de usuário. Se não existirem ou estiverem
        expiradas, inicia o fluxo de autorização.
        """
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # Se não há credenciais válidas, permite que o usuário faça login.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Falha ao renovar token, iniciando novo login: {e}")
                    creds = self._run_auth_flow()
            else:
                creds = self._run_auth_flow()
            
            # Salva as credenciais para as próximas execuções
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        return creds

    def _run_auth_flow(self) -> Optional[Credentials]:
        """Inicia o fluxo de autorização OAuth 2.0."""
        if not os.path.exists(CREDENTIALS_FILE):
            logger.critical(f"Arquivo de credenciais '{CREDENTIALS_FILE}' não encontrado. Por favor, baixe-o do Google Cloud Console.")
            return None
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        return creds

    def list_files(self, folder_id: Optional[str] = None, page_size: int = 10) -> List[Dict]:
        """Lista os arquivos e pastas."""
        if not self.drive_service: return []
        try:
            query = f"'{folder_id}' in parents" if folder_id else None
            results = self.drive_service.files().list(
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            return results.get('files', [])
        except HttpError as error:
            logger.error(f"Erro ao listar arquivos: {error}")
            return []

    def find_file_by_name(self, filename: str) -> Optional[Dict]:
        """Encontra o primeiro arquivo ou pasta com o nome especificado."""
        files = self.list_files(page_size=100) # Aumenta o page size para melhorar a chance de encontrar
        for file in files:
            if file.get('name', '').lower() == filename.lower():
                logger.info(f"Arquivo '{filename}' encontrado com ID: {file.get('id')}")
                return file
        logger.warning(f"Arquivo '{filename}' não encontrado.")
        return None

    def read_doc_content(self, file_id: str) -> Optional[str]:
        """Lê o conteúdo de um arquivo Google Docs."""
        if not self.docs_service: return None
        try:
            doc = self.docs_service.documents().get(documentId=file_id).execute()
            content = doc.get('body', {}).get('content', [])
            return self._read_structural_elements(content)
        except HttpError as error:
            logger.error(f"Erro ao ler documento: {error}")
            return None

    def _read_structural_elements(self, elements: List) -> str:
        """Processa os elementos estruturais de um Google Doc para extrair o texto."""
        text = ""
        for value in elements:
            if 'paragraph' in value:
                elements = value.get('paragraph').get('elements')
                for elem in elements:
                    if 'textRun' in elem:
                        text += elem.get('textRun').get('content')
        return text

    def create_doc(self, title: str, content: str, folder_id: Optional[str] = None) -> Optional[Dict]:
        """Cria um novo Google Doc com o título e conteúdo especificados."""
        if not self.drive_service or not self.docs_service: return None
        try:
            # 1. Cria um documento em branco no Drive
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document'
            }
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            file = self.drive_service.files().create(body=file_metadata, fields='id').execute()
            doc_id = file.get('id')
            logger.info(f"Documento em branco criado com ID: {doc_id}")

            # 2. Insere o conteúdo no documento recém-criado
            requests = [
                {
                    'insertText': {
                        'location': { 'index': 1 },
                        'text': content
                    }
                }
            ]
            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}
            ).execute()
            logger.info("Conteúdo inserido no novo documento.")
            return file
        except HttpError as error:
            logger.error(f"Erro ao criar documento: {error}")
            return None
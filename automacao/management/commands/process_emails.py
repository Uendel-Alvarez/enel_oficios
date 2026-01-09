import os
import unicodedata
import pdfplumber
import re
import warnings
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_aware, now
from django.conf import settings
from imap_tools import MailBox
from automacao.models import OficioEnel
from automacao.utils import importar_itens_seguro

# Silencia avisos de formatação do Excel (openpyxl) para limpar o terminal
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- NOVO FILTRO DE SEGURANÇA E PALAVRAS-CHAVE ---
def validar_assunto_email(assunto):
    """
    Verifica se o assunto contém as palavras-chave do cliente
    e bloqueia termos indesejados (ex: Supabase).
    """
    if not assunto:
        return False
        
    assunto_clean = assunto.upper()
    
    # Lista fornecida pelo Cliente (incluindo variações com/sem acento e siglas)
    keywords = [
        "OFÍCIO", "OFICIO", "OF ", "ILUMINAÇÃO", "ILUMINACAO", "PÚBLICA", "PUBLICA",
        "ATUALIZAÇÃO", "ATUALIZACAO", "PARQUE", "ILUM", "ATUAL", "TROCA", "LÂMPADA", 
        "LAMPADA", "IP", "AJUSTE", "CORREÇÃO", "CORRECAO", "SUBSTITUIÇÃO", 
        "SUBSTITUICAO", "ILUMP", "ENEL"
    ]
    
    # Termos de exclusão (Blacklist) para evitar capturar e-mails técnicos ou propagandas
    blacklist = ["SUPABASE", "PROJECT ENEL", "NOREPLY", "NEWSLETTER"]
    
    # 1. Se contiver algo da blacklist, descarta na hora
    if any(term in assunto_clean for term in blacklist):
        return False
        
    # 2. Se contiver qualquer uma das palavras-chave, aprova
    return any(key in assunto_clean for key in keywords)


# --- FUNÇÃO AUXILIAR DE EXTRAÇÃO ---
def processar_arquivo_individual(caminho_arquivo, objeto_oficio):
    extensao = caminho_arquivo.lower()
    
    if extensao.endswith('.pdf'):
        try:
            with pdfplumber.open(caminho_arquivo) as pdf:
                texto = "".join([page.extract_text() or "" for page in pdf.pages])
                
                padrao_of = re.search(r"(?:OFÍCIO|OF|Ofício)\s*(?:N°|NO|N|/|nº)?\s*([A-Za-z0-9/\-\.]+)", texto, re.IGNORECASE)
                if padrao_of: 
                    objeto_oficio.numero_protocolo = padrao_of.group(0).strip()
                
                padrao_mun = re.search(r"(?:Município de|PREFEITURA MUNICIPAL DE)\s+([A-ZÀ-Ú\s\-]{3,})", texto, re.IGNORECASE)
                if padrao_mun: 
                    objeto_oficio.municipio = padrao_mun.group(1).strip().split('\n')[0][:50]
                
                objeto_oficio.save()
        except Exception as e:
            print(f"Erro ao ler PDF: {e}")

    elif extensao.endswith(('.xlsx', '.xls')):
        try:
            importar_itens_seguro(caminho_arquivo, objeto_oficio)
        except Exception as e:
            print(f"Erro ao processar planilha: {e}")

def executar_captura():
    EMAIL_HOST = 'imap.gmail.com'
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

    if not EMAIL_USER or not EMAIL_PASSWORD:
        return "Erro: Credenciais ausentes no .env"

    try:
        with MailBox(EMAIL_HOST).login(EMAIL_USER, EMAIL_PASSWORD) as mailbox:
            # Aumentei o limite para 20 para garantir que pegamos os mais recentes após o filtro
            for msg in mailbox.fetch(limit=20, reverse=True): 
                
                # --- APLICAÇÃO DO FILTRO DE ASSUNTO ---
                if not validar_assunto_email(msg.subject):
                    print(f"⏭️ Ignorado (Filtro): {msg.subject}")
                    continue

                # Evita duplicidade
                if OficioEnel.objects.filter(assunto=msg.subject, data_recebimento=msg.date).exists():
                    continue

                print(f"✅ Processando: {msg.subject}")
                
                data_email = msg.date if is_aware(msg.date) else make_aware(msg.date)
                
                # Cria o registro apenas se passar no filtro
                novo_oficio = OficioEnel.objects.create(
                    assunto=msg.subject,
                    data_recebimento=data_email,
                    remetente=msg.from_,
                    corpo_email=msg.text[:500] if msg.text else "Captura via E-mail",
                    status_processamento=0
                )

                download_path = os.path.join(settings.MEDIA_ROOT, 'anexos')
                if not os.path.exists(download_path): os.makedirs(download_path)

                for att in msg.attachments:
                    caminho_arquivo = os.path.join(download_path, att.filename)
                    with open(caminho_arquivo, 'wb') as f:
                        f.write(att.payload)
                    
                    processar_arquivo_individual(caminho_arquivo, novo_oficio)

        return "Captura de e-mail finalizada com sucesso."
    except Exception as e:
        return f"Erro: {e}"

class Command(BaseCommand):
    help = 'Executa a captura de e-mails da ENEL'
    def handle(self, *args, **options):
        msg = executar_captura()
        self.stdout.write(msg)
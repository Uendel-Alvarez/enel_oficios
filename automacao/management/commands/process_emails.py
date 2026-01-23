import os
import re
import warnings
import pdfplumber
import time
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_aware
from django.conf import settings
from django.core.files import File
from imap_tools import MailBox
from automacao.models import OficioEnel, AnexoOficio, importar_itens_seguro
from automacao.utils_ia import extrair_dados_oficio

# Silencia avisos de Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

def validar_assunto_email(assunto):
    if not assunto: return False
    assunto_clean = assunto.upper()
    keywords = [
        "OFÍCIO", "OFICIO", "OF ", "ILUMINAÇÃO", "ILUMINACAO", "PÚBLICA", "PUBLICA",
        "ATUALIZAÇÃO", "ATUALIZACAO", "PARQUE", "ILUM", "ATUAL", "TROCA", "LÂMPADA", 
        "LAMPADA", "IP", "AJUSTE", "CORREÇÃO", "CORRECAO", "SUBSTITUIÇÃO", 
        "SUBSTITUICAO", "ILUMP", "ENEL"
    ]
    blacklist = ["SUPABASE", "PROJECT ENEL", "NOREPLY", "NEWSLETTER"]
    if any(term in assunto_clean for term in blacklist): return False
    return any(key in assunto_clean for key in keywords)

def processar_arquivo_individual(caminho_arquivo, objeto_oficio):
    extensao = caminho_arquivo.lower()
    dados_ia = None

    # Delay para respeitar cota da API Gemini gratuita
    print(f"⏳ Aguardando janela da API Gemini (Rate Limit - 40s)... ({os.path.basename(caminho_arquivo)})")
    time.sleep(40)
    
    if extensao.endswith('.pdf'):
        try:
            texto_extraido = ""
            with pdfplumber.open(caminho_arquivo) as pdf:
                texto_extraido = "".join([page.extract_text() or "" for page in pdf.pages])
            
            # Se PDF for imagem (scan), vai direto para IA
            if len(texto_extraido.strip()) < 20:
                print(f"📸 PDF detectado como imagem/scan. Acionando IA OCR...")
                dados_ia = extrair_dados_oficio(caminho_arquivo)
            else:
                # Tenta Regex para campos básicos
                padrao_of = re.search(r"(?:OFÍCIO|OF|Ofício)\s*(?:N°|NO|N|/|nº)?\s*([A-Za-z0-9/\-\.]+)", texto_extraido, re.IGNORECASE)
                if padrao_of: 
                    objeto_oficio.numero_protocolo = padrao_of.group(1).strip()
                
                padrao_mun = re.search(r"(?:Município de|PREFEITURA MUNICIPAL DE)\s+([A-ZÀ-Ú\s\-]{3,})", texto_extraido, re.IGNORECASE)
                if padrao_mun: 
                    objeto_oficio.municipio = padrao_mun.group(1).strip().split('\n')[0][:50]

                # Se falhar, IA assume
                if not objeto_oficio.municipio or "NÃO ENCONTRADO" in str(objeto_oficio.municipio):
                    dados_ia = extrair_dados_oficio(caminho_arquivo)

        except Exception as e:
            print(f"❌ Erro ao processar PDF: {e}")

    elif extensao.endswith(('.xlsx', '.xls')):
        print(f"🤖 Processando planilha técnica...")
        # A IA identifica os dados de cabeçalho mesmo na planilha
        dados_ia = extrair_dados_oficio(caminho_arquivo)
        try:
            importar_itens_seguro(caminho_arquivo, objeto_oficio)
        except Exception as e:
            print(f"Erro na importação de itens: {e}")

    # Atualiza o objeto com os dados da IA
    if dados_ia and isinstance(dados_ia, dict):
        if dados_ia.get("numero_protocolo") != "NÃO ENCONTRADO":
            objeto_oficio.numero_protocolo = dados_ia.get("numero_protocolo")
        if dados_ia.get("municipio") != "NÃO ENCONTRADO":
            objeto_oficio.municipio = dados_ia.get("municipio")
        if dados_ia.get("orgao_solicitante"):
            objeto_oficio.orgao_solicitante = dados_ia.get("orgao_solicitante")

    # Se capturou os dados mínimos, marca como Concluído
    if objeto_oficio.numero_protocolo and objeto_oficio.municipio:
        objeto_oficio.status_processamento = 1
    
    objeto_oficio.save()

def executar_captura():
    EMAIL_HOST = 'imap.gmail.com'
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

    if not EMAIL_USER or not EMAIL_PASSWORD: return "Erro: Credenciais ausentes"

    try:
        with MailBox(EMAIL_HOST).login(EMAIL_USER, EMAIL_PASSWORD) as mailbox:
            for msg in mailbox.fetch(limit=20, reverse=True): 
                if not validar_assunto_email(msg.subject): continue

                data_email = msg.date if is_aware(msg.date) else make_aware(msg.date)
                if OficioEnel.objects.filter(assunto=msg.subject, data_recebimento=data_email).exists():
                    continue

                print(f"📩 Novo E-mail: {msg.subject}")
                
                novo_oficio = OficioEnel.objects.create(
                    assunto=msg.subject,
                    data_recebimento=data_email,
                    remetente=msg.from_,
                    corpo_email=msg.text[:500] if msg.text else "",
                    status_processamento=0,
                    quantidade_anexos=len(msg.attachments)
                )

                download_path = os.path.join(settings.MEDIA_ROOT, 'anexos')
                if not os.path.exists(download_path): os.makedirs(download_path)

                pdf_principal_definido = False

                for att in msg.attachments:
                    nome_arquivo = att.filename
                    caminho_temp = os.path.join(download_path, nome_arquivo)
                    
                    # Salva arquivo temporariamente
                    with open(caminho_temp, 'wb') as f:
                        f.write(att.payload)
                    
                    # 1. SALVA NA NOVA TABELA DE ANEXOS (Garante que nenhum arquivo se perca)
                    with open(caminho_temp, 'rb') as f:
                        anexo_obj = AnexoOficio.objects.create(
                            oficio=novo_oficio,
                            nome_original=nome_arquivo
                        )
                        anexo_obj.arquivo.save(nome_arquivo, File(f), save=True)

                    # 2. DEFINE O PDF COMO O ARQUIVO DE VISUALIZAÇÃO PRINCIPAL
                    if nome_arquivo.lower().endswith('.pdf') and not pdf_principal_definido:
                        novo_oficio.caminho_arquivo = os.path.join('anexos', nome_arquivo)
                        novo_oficio.save()
                        pdf_principal_definido = True
                    
                    # Se não tiver PDF, a planilha fica como principal temporariamente
                    elif not pdf_principal_definido and nome_arquivo.lower().endswith(('.xlsx', '.xls')):
                        novo_oficio.caminho_arquivo = os.path.join('anexos', nome_arquivo)
                        novo_oficio.save()

                    # 3. PROCESSA IA/OCR
                    processar_arquivo_individual(caminho_temp, novo_oficio)

        return "Captura finalizada com sucesso."
    except Exception as e:
        return f"Erro: {e}"

class Command(BaseCommand):
    help = 'Executa a captura de e-mails da ENEL'
    def handle(self, *args, **options):
        self.stdout.write(executar_captura())
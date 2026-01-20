import os
import re
import warnings
import pdfplumber
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_aware
from django.conf import settings
from imap_tools import MailBox
from automacao.models import OficioEnel, importar_itens_seguro
from automacao.utils_ia import extrair_dados_oficio
import time

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

    # 1. DELAY ESTRATÉGICO PARA PLANO GRATUITO (Erro 429)
    # Aumentamos para 40 segundos pois o log mostrou que 10s não é suficiente para o Google liberar a cota
    print(f"⏳ Aguardando janela da API Gemini (Rate Limit - 40s)...")
    time.sleep(40)
    
    if extensao.endswith('.pdf'):
        try:
            # 2. TENTATIVA RÁPIDA COM REGEX (Seu código original)
            with pdfplumber.open(caminho_arquivo) as pdf:
                texto = "".join([page.extract_text() or "" for page in pdf.pages])
                
                padrao_of = re.search(r"(?:OFÍCIO|OF|Ofício)\s*(?:N°|NO|N|/|nº)?\s*([A-Za-z0-9/\-\.]+)", texto, re.IGNORECASE)
                if padrao_of: 
                    objeto_oficio.numero_protocolo = padrao_of.group(0).strip()
                
                padrao_mun = re.search(r"(?:Município de|PREFEITURA MUNICIPAL DE)\s+([A-ZÀ-Ú\s\-]{3,})", texto, re.IGNORECASE)
                if padrao_mun: 
                    objeto_oficio.municipio = padrao_mun.group(1).strip().split('\n')[0][:50]

            # 3. SE REGEX FALHAR OU PDF FOR IMAGEM, CHAMA A IA
            if not objeto_oficio.municipio or not objeto_oficio.numero_protocolo or not texto.strip():
                print(f"🤖 IA processando extração profunda: {os.path.basename(caminho_arquivo)}")
                try:
                    dados_ia = extrair_dados_oficio(caminho_arquivo)
                    if dados_ia and isinstance(dados_ia, dict):
                        if dados_ia.get("numero_protocolo") != "NÃO ENCONTRADO":
                            objeto_oficio.numero_protocolo = dados_ia.get("numero_protocolo")
                        if dados_ia.get("municipio") != "NÃO ENCONTRADO":
                            objeto_oficio.municipio = dados_ia.get("municipio")
                        objeto_oficio.orgao_solicitante = dados_ia.get("orgao_solicitante")
                except Exception as e_ia:
                    print(f"⚠️ IA falhou (possível cota excedida): {e_ia}")

            # SALVA O CABEÇALHO IMEDIATAMENTE
            objeto_oficio.save()
            print(f"✅ Cabeçalho atualizado no Admin: {objeto_oficio.municipio} - {objeto_oficio.numero_protocolo}")

        except Exception as e:
            print(f"❌ Erro ao ler PDF: {e}")

    elif extensao.endswith(('.xlsx', '.xls')):
        try:
            # IA identifica os dados básicos da planilha
            print(f"🤖 IA identificando cabeçalho da planilha...")
            try:
                dados_ia = extrair_dados_oficio(caminho_arquivo)
                if dados_ia and isinstance(dados_ia, dict):
                    objeto_oficio.municipio = dados_ia.get("municipio")
                    objeto_oficio.numero_protocolo = dados_ia.get("numero_protocolo")
                    objeto_oficio.save()
            except Exception as e_ia:
                print(f"⚠️ IA falhou na planilha: {e_ia}")

            # 4. PROCESSA OS ITENS TÉCNICOS (Pandas)
            # O cabeçalho já foi salvo, então se o IDG falhar, o Município já está no Admin
            importar_itens_seguro(caminho_arquivo, objeto_oficio)
            
        except Exception as e:
            print(f"Erro na planilha (Itens não importados, mas cabeçalho OK): {e}")
def executar_captura():
    EMAIL_HOST = 'imap.gmail.com'
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

    if not EMAIL_USER or not EMAIL_PASSWORD: return "Erro: Credenciais ausentes"

    try:
        with MailBox(EMAIL_HOST).login(EMAIL_USER, EMAIL_PASSWORD) as mailbox:
            for msg in mailbox.fetch(limit=20, reverse=True): 
                if not validar_assunto_email(msg.subject): continue

                # Só ignora se o ofício já existir E tiver município preenchido
                if OficioEnel.objects.filter(assunto=msg.subject, data_recebimento=msg.date).exclude(municipio='').exists():
                    continue

                print(f"📩 Capturando: {msg.subject}")
                data_email = msg.date if is_aware(msg.date) else make_aware(msg.date)
                
                # Cria ou recupera o registo
                novo_oficio, created = OficioEnel.objects.get_or_create(
                    assunto=msg.subject,
                    data_recebimento=data_email,
                    defaults={
                        'remetente': msg.from_,
                        'corpo_email': msg.text[:500] if msg.text else "Captura via E-mail",
                        'status_processamento': 0
                    }
                )

                download_path = os.path.join(settings.MEDIA_ROOT, 'anexos')
                if not os.path.exists(download_path): os.makedirs(download_path)

                for att in msg.attachments:
                    caminho_arquivo = os.path.join(download_path, att.filename)
                    with open(caminho_arquivo, 'wb') as f:
                        f.write(att.payload)
                    processar_arquivo_individual(caminho_arquivo, novo_oficio)

        return "Processamento concluído."
    except Exception as e:
        return f"Erro: {e}"

class Command(BaseCommand):
    help = 'Executa a captura de e-mails da ENEL'
    def handle(self, *args, **options):
        self.stdout.write(executar_captura())
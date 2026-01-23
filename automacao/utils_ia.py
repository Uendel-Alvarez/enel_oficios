import os
import json
import pandas as pd
import warnings
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Silencia avisos de validação do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

load_dotenv()

# --- CONFIGURAÇÃO DA CHAVE DIRETA ---
# Cole sua chave entre as aspas. Verifique se não há espaços extras.
API_KEY_DIRETA = "AIzaSyCbyL9bkVNWwu0HkPCA_Q3HatzZ0ESa8JI" 
genai.configure(api_key=API_KEY_DIRETA)

# PROMPT DE ANÁLISE TÉCNICA
PROMPT_DEEP_ANALYSIS = """
Aja como um Perito em Documentos Públicos da Enel Rio. Sua missão é extrair dados técnicos de ofícios municipais.

INSTRUÇÕES DE ANÁLISE:
1. municipio: Identifique pelo brasão, timbre ou cabeçalho. Extraia apenas o nome da cidade.
2. numero_protocolo: Procure por "Ofício nº", "OF/", "GAPE", "SUOSU". Capture o identificador completo.
3. data: Formate como DD/MM/AAAA.
4. orgao_solicitante: Secretaria, Subprefeitura ou Gabinete.
5. assunto: Resumo do objetivo (ex: Troca de LED, Iluminação de Praça).
6. pedidos_servicos: Detalhes técnicos (quantidade, potência W, tecnologia).

REGRAS:
- Responda EXCLUSIVAMENTE em formato JSON puro.
- Se não encontrar um campo, use "NÃO ENCONTRADO".

{
  "numero_protocolo": "...",
  "municipio": "...",
  "data": "...",
  "orgao_solicitante": "...",
  "assunto": "...",
  "pedidos_servicos": "..."
}
"""

def extrair_dados_oficio(caminho_arquivo):
    """
    Extrai dados de PDF ou Excel usando Gemini 2.0 Flash.
    """
    try:
        if not os.path.exists(caminho_arquivo):
            print(f"⚠️ Arquivo não encontrado: {caminho_arquivo}")
            return None

        # Usando o modelo confirmado pela sua lista de modelos
        model = genai.GenerativeModel('gemini-2.0-flash')
        #Opção de modelo alternativo
        #model = genai.GenerativeModel('gemini-2.0-flash-lite')

        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        if extensao == '.pdf':
            # Upload do arquivo para a infra do Google
            arquivo_gemini = genai.upload_file(path=caminho_arquivo)
            
            # Tempo necessário para o servidor processar o arquivo antes da análise
            time.sleep(3)
            
            response = model.generate_content([PROMPT_DEEP_ANALYSIS, arquivo_gemini])
        
        elif extensao in ['.xlsx', '.xls']:
            df_topo = pd.read_excel(caminho_arquivo).iloc[:50, :15]
            texto_excel = df_topo.to_string()
            response = model.generate_content(f"{PROMPT_DEEP_ANALYSIS}\n\nCONTEÚDO DA PLANILHA:\n{texto_excel}")
        
        else:
            return None

        # Extração e limpeza do JSON
        txt = response.text.strip()
        # Remove blocos de código markdown se houver
        txt_limpo = re.sub(r'```json\s*|```', '', txt).strip()
        
        # Converte para dicionário Python
        return json.loads(txt_limpo)

    except Exception as e:
        print(f"❌ Erro na IA: {e}")
        return {
            "numero_protocolo": "ERRO TÉCNICO",
            "municipio": "VERIFICAR LOGS",
            "data": "---",
            "orgao_solicitante": "---",
            "assunto": f"Erro: {str(e)[:50]}",
            "pedidos_servicos": "Falha na comunicação."
        }
    
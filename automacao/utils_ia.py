import os
import json
import pandas as pd
import warnings
from google import genai
from google.genai import types 
from dotenv import load_dotenv

# Silencia avisos de validação do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# PROMPT 1: Focado nos campos da classe OficioEnel
PROMPT_OFICIO = """
Aja como um analista de documentos da Enel Rio. Analise visualmente este Ofício e extraia:
- numero_protocolo: O número do ofício ou protocolo (ex: 177/2026).
- municipio: Nome da cidade beneficiada.
- orgao_solicitante: Qual secretaria ou órgão assina (ex: Secretaria de Obras).
- assunto: Um resumo curto do que se trata o documento.

Responda APENAS em JSON:
{"numero_protocolo": "...", "municipio": "...", "orgao_solicitante": "...", "assunto": "..."}
"""

# PROMPT 2: Focado em validar a planilha e extrair o cabeçalho
PROMPT_PLANILHA = """
Analise os dados desta planilha de Iluminação Pública. Extraia os dados de identificação:
- municipio: O município citado na planilha.
- numero_protocolo: Procure por algum número de referência ou ofício no topo.

Responda APENAS em JSON:
{"municipio": "...", "numero_protocolo": "..."}
"""

def extrair_dados_oficio(caminho_arquivo):
    try:
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        if extensao == '.pdf':
            with open(caminho_arquivo, "rb") as f:
                pdf_bytes = f.read()
            conteudo = [
                PROMPT_OFICIO,
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            ]
        elif extensao in ['.xlsx', '.xls']:
            # Lemos apenas o topo para a IA não se perder nas milhares de linhas de itens
            df_topo = pd.read_excel(caminho_arquivo).iloc[:20, :10]
            conteudo = f"{PROMPT_PLANILHA}\n\nCONTEÚDO DA PLANILHA (TOPO):\n{df_topo.to_string()}"
        else:
            return None

        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=conteudo
        )

        # Limpeza do JSON
        txt = response.text.strip()
        if "```" in txt:
            txt = txt.split("```")[1].replace("json", "").strip()
            
        return json.loads(txt)

    except Exception as e:
        print(f"Erro na IA: {e}")
        return None

# --- Exemplo de como você usará isso amanhã no views.py ---
# dados_ia = extrair_dados_oficio("documento.pdf")
# OficioEnel.objects.create(**dados_ia)

#Atenção a IA deveria exminar o conteúdo da pasta C:\Users\ResTIC16\enel_oficios\media
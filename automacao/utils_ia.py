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

# Configuração do Cliente Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# PROMPT EVOLUÍDO: Focado na complexidade dos modelos de Itaperuna, Magé e Campos
PROMPT_DEEP_ANALYSIS = """
Aja como um Perito em Documentos Públicos da Enel Rio. Sua missão é extrair dados técnicos de ofícios municipais de qualquer cidade da área de concessão.

INSTRUÇÕES DE ANÁLISE VISUAL E TEXTUAL:
1. municipio: Identifique o ente federativo. Olhe para o brasão no topo, o timbre da prefeitura ou frases como "Prefeitura Municipal de...". Extraia apenas o nome da cidade.
2. numero_protocolo: Procure por identificadores de documento como "Ofício nº", "OF/", "GAPE", "SUOSU", ou qualquer numeração no topo à direita ou esquerda. Capture o identificador completo.
3. data: Busque a data de emissão. Formate como DD/MM/AAAA.
4. orgao_solicitante: Identifique qual Secretaria, Subprefeitura ou Gabinete assina o documento.
5. assunto: Resuma o objetivo do ofício (ex: Atualização de pontos, Substituição por LED, Iluminação de Praça).
6. pedidos_servicos: Extraia detalhes técnicos: quantidade de lâmpadas, potência (W), tecnologia (LED ou Vapor de Sódio) e locais citados.

REGRAS DE OURO:
- Não se limite aos nomes de cidades conhecidos; se o brasão diz "Prefeitura de [Nome]", esse é o município.
- Se o documento for um scan (foto) ruim, use sua capacidade de visão para decifrar carimbos e marcas d'água.
- Caso um campo seja impossível de ler, retorne "NÃO ENCONTRADO".
- Decifre carimbos e marcas d'água se o scan for ruim.
- Se não encontrar um campo, retorne "NÃO ENCONTRADO".
- Responda EXCLUSIVAMENTE em formato JSON puro.

Responda APENAS o JSON puro:
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
    Analisa arquivos na pasta media (mapeada no Docker ou local) 
    e utiliza o Gemini 1.5 Flash para extração multimodal.
    """
    try:
        if not os.path.exists(caminho_arquivo):
            print(f"⚠️ Arquivo não encontrado no caminho: {caminho_arquivo}")
            return None

        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        if extensao == '.pdf':
            with open(caminho_arquivo, "rb") as f:
                pdf_bytes = f.read()
            
            conteudo = [
                PROMPT_DEEP_ANALYSIS,
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            ]
        
        elif extensao in ['.xlsx', '.xls']:
            # Lemos as primeiras 50 linhas para captar cabeçalhos espalhados
            df_topo = pd.read_excel(caminho_arquivo).iloc[:50, :15]
            conteudo = f"{PROMPT_DEEP_ANALYSIS}\n\nCONTEÚDO DA PLANILHA:\n{df_topo.to_string()}"
        
        else:
            return None

        # Usando o modelo gemini-1.5-flash que é excelente para OCR e scans
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=conteudo,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Menor temperatura = mais precisão técnica
            )
        )

        # Limpeza e extração do JSON da resposta
        txt = response.text.strip()
        if "```json" in txt:
            txt = txt.split("```json")[1].split("```")[0].strip()
        elif "```" in txt:
            txt = txt.split("```")[1].strip()
            
        return json.loads(txt)

    except Exception as e:
        print(f"❌ Erro na IA (Deep Extraction): {e}")
        return None
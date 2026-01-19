import os
import fitz  # PyMuPDF
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def extrair_dados_oficio(caminho_pdf):
    # 1. Abre o PDF e extrai o texto bruto
    doc = fitz.open(caminho_pdf)
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text()

    # 2. Configura o prompt para a IA
    prompt = f"""
    Aja como um especialista em análise de documentos da Enel.
    Extraia do texto abaixo:
    1. O Nome do Município (Geralmente no cabeçalho ou vocativo).
    2. O Número do Protocolo ou Número do Ofício (Ex: 123/2026, Ofício nº 45, etc).
    
    Responda APENAS em formato JSON:
    {{"municipio": "NOME", "protocolo": "NUMERO"}}
    
    Texto:
    {texto_completo}
    """
    

    # 3. Envia para o Gemini 3 Flash
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        # Limpa a resposta para garantir que seja um JSON válido
        dados = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(dados)
    except Exception as e:
        return f"Erro no processamento: {e}"

# --- ÁREA DE TESTE ---
#Se você tiver um PDF na pasta /app, coloque o nome dele aqui:
if __name__ == "__main__":
    # Use aspas simples dentro das duplas para garantir que o nome com espaços funcione
    nome_do_arquivo = "Of 16 Cadastro parque IP.pdf"
    
    print(f"--- INICIANDO LEITURA: {nome_do_arquivo} ---")
    
    resultado = extrair_dados_oficio(nome_do_arquivo)
    
    print("\n--- RESULTADO DA IA ---")
    
    print(resultado)
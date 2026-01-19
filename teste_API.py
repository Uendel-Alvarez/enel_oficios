import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

# 1. Localiza o caminho absoluto do arquivo .env
# Isso evita que o Docker se confunda com pastas
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# 2. Busca a chave
#api_key_env = os.getenv("GEMINI_API_KEY")
# Substitua a linha antiga por esta:
api_key_env = os.getenv("GEMINI_API_KEY").strip().replace('"', '').replace("'", "")

print("--- DIAGNÓSTICO DE CARREGAMENTO ---")
if api_key_env:
    # Mostra apenas os 4 primeiros dígitos para sua segurança
    print(f"✅ Sucesso! O Python leu a chave do .env: {api_key_env[:4]}****")
else:
    print("🚨 Erro: O Python ainda não consegue ver a chave dentro do .env")
print("-----------------------------------\n")

# 3. Inicializa o cliente
client = genai.Client(api_key=api_key_env)

try:
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents="Diga apenas: Conexão Estabelecida!"
    )
    print(f"🤖 IA respondeu: {response.text}")
    print("**** Deu Bom!!! *****")

except Exception as e:
    print(f"❌ Erro na API: {e}")














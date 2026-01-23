from google import genai
import os

# COLOQUE SUA CHAVE AQUI DENTRO DAS ASPAS
MINHA_CHAVE_REAL = "AIzaSyCbyL9bkVNWwu0HkPCA_Q3HatzZ0ESa8JI"

print(f"--- TESTE MANUAL COM CHAVE DIRETA ---")

try:
    client = genai.Client(api_key=MINHA_CHAVE_REAL)
    
    # Vamos usar o modelo mais básico possível
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Oi"
    )
    print(f"✅ FINALMENTE FUNCIONOU: {response.text}")
except Exception as e:
    print(f"❌ CONTINUA DANDO ERRO.")
    print(f"MENSAGEM EXATA: {e}")
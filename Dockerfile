# 1. Usamos uma imagem leve do Python
FROM python:3.12-slim

# 2. Impede que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Define onde o código vai morar dentro do container
WORKDIR /app

# 4. Instala dependências do sistema (necessárias para o Pandas e outros)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Instala as bibliotecas do seu projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia todo o seu código para dentro do container
COPY . .

# 7. Expõe a porta que o Django usa
EXPOSE 8000
from celery import shared_task
# O caminho aponta para o arquivo dentro da pasta de comandos
from automacao.management.commands.process_emails import executar_captura

@shared_task
def tarefa_captura_emails():
    print("Executando captura automática via Celery...")
    resultado = executar_captura()
    print(f"Resultado da tarefa: {resultado}")


import os
from celery import Celery

# Define o Django como ambiente padrão
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Lê as configurações do settings.py com o prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega tarefas de todos os apps (como o seu tasks.py)
app.autodiscover_tasks()






















"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'capturar-emails-a-cada-30s': {
        'task': 'automacao.tasks.tarefa_captura_emails',
        'schedule': 30.0,
    },
}

"""
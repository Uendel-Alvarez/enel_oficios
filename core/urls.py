from django.contrib import admin
from django.urls import path
from django.conf import settings 
from django.conf.urls.static import static 
from django.contrib.auth import views as auth_views
from automacao import views  # Importa as views da pasta correta

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Dashboard e Navegação
    path('', views.home_view, name='home'),
    path('monitoramento/', views.monitoramento_view, name='monitoramento'),
    path('oficios/', views.listagem_oficios, name='listagem_oficios'),
    
    # Gestão de Ofícios
    path('oficios/pendentes/', views.listagem_pendentes, name='listagem_pendentes'),
    path('upload-manual/', views.upload_manual, name='upload_manual'),
    path('oficio/editar/<int:pk>/', views.editar_oficio, name='editar_oficio'),
    path('oficio/detalhe/<int:oficio_id>/', views.oficio_detalhe_fragmento, name='oficio_detalhe_fragmento'),
    
    # Ferramentas
    path('exportar-csv/', views.exportar_oficios_csv, name='exportar_oficios_csv'),
    
    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Servir arquivos de mídia (PDFs e Planilhas) em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
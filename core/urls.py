
from django.contrib import admin
from django.urls import path
from django.conf import settings 
from django.conf.urls.static import static 
from automacao.views import monitoramento_view, home_view, listagem_oficios
from automacao import views
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('monitoramento/', monitoramento_view, name='monitoramento'),
    path('oficios/', listagem_oficios, name='listagem_oficios'),
    path('', home_view, name='home'), # A string vazia '' define a página inicial
    path('exportar-csv/', views.exportar_oficios_csv, name='exportar_oficios_csv'),
    path('oficios/pendentes/', views.listagem_pendentes, name='listagem_pendentes'),
    path('oficios/editar/<int:pk>/', views.editar_oficio, name='editar_oficio'),
    path('upload-manual/', views.upload_manual, name='upload_manual'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('oficio/editar/<int:pk>/', views.editar_oficio, name='editar_oficio'),
]

# Esta linha é essencial para o botão "VER PDF" funcionar
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
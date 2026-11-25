from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # RUTAS DE GESTIÓN DE USUARIOS
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.crear_editar_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:user_id>/', views.crear_editar_usuario, name='editar_usuario'),
    path('usuarios/toggle/<int:user_id>/', views.toggle_usuario, name='toggle_usuario'),

    path('', RedirectView.as_view(url='/inicio/', permanent=False)),
    path('inicio/', include('inicio.urls')),
    path('clientes/', include('clientes.urls')),
    path('herramientas/', include('boletas.urls')),
    path('caja-chica/', include('caja_chica.urls')),
    path('correspondencia/', include('correspondencia.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
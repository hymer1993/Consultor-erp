from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),
    path('nuevo/', views.crear_cliente, name='crear_cliente'),
    path('editar/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('eliminar/<int:id>/', views.eliminar_cliente, name='eliminar_cliente'),
    # Las rutas nuevas del Excel:
    path('importar/', views.importar_clientes, name='importar_clientes'),
    path('plantilla/', views.descargar_plantilla, name='descargar_plantilla'),
    path('exportar/', views.exportar_clientes_excel, name='exportar_clientes'),
]
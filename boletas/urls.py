from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes_boletas, name='lista_clientes_boletas'),
    path('preview/<int:cliente_id>/', views.preview_boleta, name='preview_boleta'),
    # NUEVAS RUTAS
    path('traspasos/', views.vista_traspasos, name='vista_traspasos'),
    path('saldos-negativos/', views.vista_saldos_negativos, name='vista_saldos_negativos'),
    path('extraer-pdf/', views.vista_extraer_pdf, name='vista_extraer_pdf'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_correspondencia, name='lista_correspondencia'),
    path('crear/', views.crear_correspondencia, name='crear_correspondencia'),
    path('masiva/', views.generacion_masiva, name='generacion_masiva'),
    path('pdf/<int:carta_id>/', views.generar_pdf_carta, name='generar_pdf_carta'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.caja_chica_dashboard, name='caja_chica_dashboard'),
    path('configuracion-empresa/', views.configuracion_empresa, name='configuracion_empresa'),
    path('configuracion-conceptos/', views.configuracion_conceptos, name='configuracion_conceptos'),
    path('control-gastos/', views.control_gastos, name='control_gastos'),
    path('renumerar-recibos/', views.renumerar_recibos, name='renumerar_recibos'),
    
    path('historial-reembolsos/', views.historial_reembolsos, name='historial_reembolsos'),
    path('imprimir-reembolso/<int:reembolso_id>/', views.imprimir_reembolso, name='imprimir_reembolso'),
    path('cartas-cobro/', views.cartas_cobro_dashboard, name='cartas_cobro_dashboard'),
    path('imprimir-carta/<int:carta_id>/', views.cartas_cobro_dashboard, name='imprimir_carta'),
    path('imprimir-recibo/<int:recibo_id>/<str:tipo>/', views.imprimir_recibo_pdf, name='imprimir_recibo_pdf'),
    path('imprimir-recibo-rango/', views.imprimir_recibo_rango, name='imprimir_recibo_rango'),
    
    # Rutas de Rendición
    path('rendicion/', views.rendicion_fondos, name='rendicion_fondos'),
    path('rendicion/vincular/<int:sol_id>/', views.vincular_recibos, name='vincular_recibos'),
    path('rendicion/cerrar/<int:sol_id>/', views.cerrar_rendicion, name='cerrar_rendicion'),
    path('rendicion/desvincular/<int:rec_id>/', views.desvincular_recibo, name='desvincular_recibo'),
    path('rendicion/revertir/<int:sol_id>/', views.revertir_rendicion, name='revertir_rendicion'),
    path('rendicion/imprimir/<int:sol_id>/', views.imprimir_rendicion_completa, name='imprimir_rendicion_completa'),
    
    # Reversiones y Confirmaciones
    path('revertir-reembolso/<int:reembolso_id>/', views.revertir_reembolso, name='revertir_reembolso'),
    path('revertir-carta/<int:carta_id>/', views.revertir_carta, name='revertir_carta'),
    path('desanular-recibo/<int:recibo_id>/', views.desanular_recibo, name='desanular_recibo'),
    path('confirmar-reembolso/<int:reembolso_id>/', views.confirmar_pago_reembolso, name='confirmar_pago_reembolso'),
    path('confirmar-carta/<int:carta_id>/', views.confirmar_pago_carta, name='confirmar_pago_carta'),
    path('desmarcar-reembolso/<int:reembolso_id>/', views.desmarcar_pago_reembolso, name='desmarcar_pago_reembolso'),
    path('desmarcar-carta/<int:carta_id>/', views.desmarcar_pago_carta, name='desmarcar_pago_carta'),
    path('imprimir-solicitud/<int:sol_id>/', views.imprimir_solicitud_pdf, name='imprimir_solicitud_pdf'),
]
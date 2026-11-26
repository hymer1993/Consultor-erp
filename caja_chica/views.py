from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from decimal import Decimal, InvalidOperation
from .models import ReciboCajaChica, SolicitudCajaChica, ConceptoGasto, ConfiguracionEmpresa, ReembolsoEmpleado, CartaCobro
from correspondencia.models import ControlCorrespondencia
from clientes.models import Cliente
from django.contrib.auth.models import User
import datetime

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def clean_decimal(value):
    if not value:
        return Decimal('0.00')
    val_str = str(value).strip()
    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return Decimal(val_str)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')

@login_required
def caja_chica_dashboard(request):
    accion = request.GET.get('accion', '')
    recibo_id = request.GET.get('id')
    sol_id = request.GET.get('id_sol') 
    
    recibos = ReciboCajaChica.objects.all().order_by('-fecha', '-id')
    solicitudes = SolicitudCajaChica.objects.all().order_by('-id')
    clientes = Cliente.objects.all()
    conceptos_gasto = ConceptoGasto.objects.all()
    usuarios = User.objects.all()
    
    config_empresa, created = ConfiguracionEmpresa.objects.get_or_create(id=1)

    recibo_editar = None
    if recibo_id:
        recibo_editar = get_object_or_404(ReciboCajaChica, id=recibo_id)
        
    solicitud_editar = None
    if sol_id:
        solicitud_editar = get_object_or_404(SolicitudCajaChica, id=sol_id)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'guardar_recibo':
            dia = int(request.POST.get('dia', datetime.date.today().day))
            mes = int(request.POST.get('mes', datetime.date.today().month))
            anio = int(request.POST.get('anio', datetime.date.today().year))
            fecha_recibo = datetime.date(anio, mes, dia)
            
            with transaction.atomic():
                if recibo_editar:
                    recibo = recibo_editar
                else:
                    ultimo = ReciboCajaChica.objects.order_by('-id').first()
                    max_seq = 0
                    if ultimo:
                        try: max_seq = int(ultimo.numero.split('-')[1])
                        except Exception: max_seq = ultimo.id
                    nuevo_num = f"REC-{str(max_seq + 1).zfill(5)}"
                    recibo = ReciboCajaChica(numero=nuevo_num, creado_por=request.user)

                recibo.fecha = fecha_recibo
                recibo.lugar = request.POST.get('lugar')
                recibo.tercero_nombre = request.POST.get('tercero_nombre')
                recibo.nit_ci = request.POST.get('nit_ci')
                recibo.concepto = request.POST.get('concepto')
                recibo.concepto_gasto_id = request.POST.get('concepto_gasto_id') or None
                recibo.tipo_retencion = request.POST.get('tipo_retencion')
                
                bruto = clean_decimal(request.POST.get('imp_total', 0))
                ret_iva = clean_decimal(request.POST.get('ret_iva', 0))
                ret_iue = clean_decimal(request.POST.get('ret_iue', 0))
                ret_it = clean_decimal(request.POST.get('ret_it', 0))
                
                recibo.total_bruto = bruto
                recibo.retencion_rc_iva = ret_iva
                recibo.retencion_iue = ret_iue
                recibo.retencion_it = ret_it
                recibo.total_pagado = bruto - (ret_iva + ret_iue + ret_it) 
                
                recibo.factura_nro = request.POST.get('factura_nro')
                
                cli_id = request.POST.get('cliente_id')
                if cli_id: recibo.cliente_id = cli_id
                recibo.asumido_por_cliente = 'asumido_por_cliente' in request.POST
                
                recibo.save()
                
            messages.success(request, f"Recibo {recibo.numero} guardado exitosamente.")
            return redirect(f'/caja-chica/?id={recibo.id}')

        elif form_type == 'anular_recibo' and recibo_editar:
            if recibo_editar.devuelto_al_empleado or recibo_editar.cobrado_al_cliente:
                messages.error(request, "No se puede anular un recibo ya reembolsado o cobrado.")
            else:
                recibo_editar.estado = 'anulado'
                recibo_editar.save()
                messages.warning(request, "Recibo anulado.")
            return redirect(f'/caja-chica/?id={recibo_editar.id}')

        elif form_type == 'guardar_solicitud':
            solicitante_nombre = request.POST.get('solicitante_nombre', '').strip()
            with transaction.atomic():
                usuario_obj = None
                if solicitante_nombre:
                    usuario_obj = User.objects.filter(username__iexact=solicitante_nombre).first()
                
                if not usuario_obj:
                    usuario_obj = request.user

                if solicitud_editar:
                    sol = solicitud_editar
                else:
                    ultimo = SolicitudCajaChica.objects.order_by('-id').first()
                    max_seq_sol = 0
                    if ultimo:
                        try: max_seq_sol = int(ultimo.numero_solicitud.split('-')[1])
                        except Exception: max_seq_sol = ultimo.id
                    nuevo_num = f"SOL-{str(max_seq_sol + 1).zfill(4)}"
                    
                    ultima_rendida = SolicitudCajaChica.objects.filter(estado='rendida', solicitante=usuario_obj).order_by('-id').first()
                    saldo_arrastre = ultima_rendida.saldo_final if ultima_rendida else 0
                    
                    sol = SolicitudCajaChica(
                        numero_solicitud=nuevo_num, 
                        solicitante=usuario_obj,
                        saldo_anterior=saldo_arrastre
                    )

                dia_sol = int(request.POST.get('dia_sol', datetime.date.today().day))
                mes_sol = int(request.POST.get('mes_sol', datetime.date.today().month))
                anio_sol = int(request.POST.get('anio_sol', datetime.date.today().year))
                sol.fecha_solicitud = datetime.date(anio_sol, mes_sol, dia_sol)

                sol.solicitante = usuario_obj
                sol.area = request.POST.get('area')
                sol.proveedor = request.POST.get('proveedor')
                sol.motivo_gasto = request.POST.get('motivo_gasto')
                sol.importe_solicitado = float(clean_decimal(request.POST.get('importe_solicitado', 0)))
                sol.save()
                
            messages.success(request, f"Solicitud {sol.numero_solicitud} guardada correctamente.")
            return redirect('/caja-chica/?accion=solicitud')

    hoy = datetime.date.today()
    
    ultimo_recibo_get = ReciboCajaChica.objects.order_by('-id').first()
    max_seq_get = 0
    if ultimo_recibo_get:
        try: max_seq_get = int(ultimo_recibo_get.numero.split('-')[1])
        except Exception: max_seq_get = ultimo_recibo_get.id
    proximo_numero = f"REC-{str(max_seq_get + 1).zfill(5)}"
    
    if recibo_editar:
        proximo_numero = recibo_editar.numero
        hoy = recibo_editar.fecha
        
    ultima_sol_get = SolicitudCajaChica.objects.order_by('-id').first()
    max_seq_sol_get = 0
    if ultima_sol_get:
        try: max_seq_sol_get = int(ultima_sol_get.numero_solicitud.split('-')[1])
        except Exception: max_seq_sol_get = ultima_sol_get.id
    proximo_numero_sol = f"SOL-{str(max_seq_sol_get + 1).zfill(4)}"

    context = {
        'recibos': recibos, 'solicitudes': solicitudes, 'clientes': clientes,
        'conceptos_gasto': conceptos_gasto, 'config_empresa': config_empresa,
        'recibo_editar': recibo_editar, 'solicitud_editar': solicitud_editar,
        'usuarios': usuarios, 'accion': accion, 'proximo_numero': proximo_numero,
        'proximo_numero_sol': proximo_numero_sol, 'dia_actual': hoy.day,
        'mes_actual': hoy.month, 'anio_actual': hoy.year,
    }
    return render(request, 'caja_chica/dashboard.html', context)

@login_required
def imprimir_solicitud_pdf(request, sol_id):
    solicitud = get_object_or_404(SolicitudCajaChica, id=sol_id)
    return render(request, 'caja_chica/print_solicitud.html', {
        'solicitud': solicitud,
        'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0],
    })

@login_required
def configuracion_empresa(request):
    config, created = ConfiguracionEmpresa.objects.get_or_create(id=1)
    dias_para_vencer = None
    if config.qr_vencimiento:
        dias_para_vencer = (config.qr_vencimiento - datetime.date.today()).days

    if request.method == 'POST':
        config.nombre = request.POST.get('nombre')
        config.nit = request.POST.get('nit')
        config.direccion = request.POST.get('direccion')
        config.rep_nombre = request.POST.get('rep_nombre')
        config.rep_cargo = request.POST.get('rep_cargo')
        
        fecha_venc = request.POST.get('qr_vencimiento')
        if fecha_venc:
            config.qr_vencimiento = datetime.datetime.strptime(fecha_venc, '%Y-%m-%d').date()
        else:
            config.qr_vencimiento = None

        if 'logo' in request.FILES: config.logo = request.FILES['logo']
        if 'logo_marca_agua' in request.FILES: config.logo_marca_agua = request.FILES['logo_marca_agua']
        if 'qr_cobro' in request.FILES: config.qr_cobro = request.FILES['qr_cobro']
        if 'rep_firma' in request.FILES: config.rep_firma = request.FILES['rep_firma']

        config.save()
        
        if config.qr_vencimiento:
            dias_para_vencer = (config.qr_vencimiento - datetime.date.today()).days

        messages.success(request, "Configuración de la empresa guardada exitosamente.")
        return redirect('configuracion_empresa')
        
    return render(request, 'caja_chica/configuracion_empresa.html', {
        'config': config,
        'dias_para_vencer': dias_para_vencer
    })

@login_required
def configuracion_conceptos(request):
    conceptos = ConceptoGasto.objects.all().order_by('nombre')
    accion = request.GET.get('accion', '')
    concepto_id = request.GET.get('id')
    concepto_seleccionado = None
    codigo_debe_edit, nombre_debe_edit, codigo_haber_edit, nombre_haber_edit = '', '', '', ''

    if concepto_id:
        concepto_seleccionado = get_object_or_404(ConceptoGasto, id=concepto_id)
        partes_debe = concepto_seleccionado.cuenta_debe.split(' ', 1)
        codigo_debe_edit = partes_debe[0] if len(partes_debe) > 0 else ''
        nombre_debe_edit = partes_debe[1] if len(partes_debe) > 1 else ''
        partes_haber = concepto_seleccionado.cuenta_haber.split(' ', 1)
        codigo_haber_edit = partes_haber[0] if len(partes_haber) > 0 else ''
        nombre_haber_edit = partes_haber[1] if len(partes_haber) > 1 else ''

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'guardar':
            nombre = request.POST.get('nombre')
            c_debe = request.POST.get('codigo_debe', '').strip()
            n_debe = request.POST.get('nombre_debe', '').strip()
            cuenta_debe = f"{c_debe} {n_debe}".strip()
            c_haber = request.POST.get('codigo_haber', '').strip()
            n_haber = request.POST.get('nombre_haber', '').strip()
            cuenta_haber = f"{c_haber} {n_haber}".strip()
            
            if nombre and cuenta_debe and cuenta_haber:
                if concepto_id:
                    concepto_seleccionado.nombre = nombre
                    concepto_seleccionado.cuenta_debe = cuenta_debe
                    concepto_seleccionado.cuenta_haber = cuenta_haber
                    concepto_seleccionado.save()
                    messages.success(request, f"Concepto '{nombre}' actualizado correctamente.")
                else:
                    nuevo = ConceptoGasto.objects.create(nombre=nombre, cuenta_debe=cuenta_debe, cuenta_haber=cuenta_haber)
                    messages.success(request, f"Concepto '{nombre}' creado correctamente.")
                    concepto_id = nuevo.id 
                return redirect(f'/caja-chica/configuracion-conceptos/?id={concepto_id}')

        elif form_type == 'eliminar' and concepto_seleccionado:
            nombre = concepto_seleccionado.nombre
            concepto_seleccionado.delete()
            messages.success(request, f"Concepto '{nombre}' eliminado.")
            return redirect('configuracion_conceptos')
            
    return render(request, 'caja_chica/configuracion_conceptos.html', {
        'conceptos': conceptos, 'concepto_seleccionado': concepto_seleccionado, 'accion': accion, 'concepto_id': concepto_id,
        'codigo_debe_edit': codigo_debe_edit, 'nombre_debe_edit': nombre_debe_edit, 'codigo_haber_edit': codigo_haber_edit, 'nombre_haber_edit': nombre_haber_edit,
    })

@login_required
def control_gastos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cliente_id = request.GET.get('cliente_id')
    empleado_sel = request.GET.get('empleado', '')
    estado_sel = request.GET.get('estado', '')
    
    recibos = ReciboCajaChica.objects.all().order_by('-fecha')
    
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.datetime.strptime(fecha_inicio, '%d/%m/%Y').date()
            recibos = recibos.filter(fecha__gte=fecha_inicio_dt)
        except ValueError: pass
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.datetime.strptime(fecha_fin, '%d/%m/%Y').date()
            recibos = recibos.filter(fecha__lte=fecha_fin_dt)
        except ValueError: pass
    if cliente_id: recibos = recibos.filter(cliente_id=cliente_id)
    if empleado_sel: recibos = recibos.filter(tercero_nombre__icontains=empleado_sel)
        
    if estado_sel == 'pendiente_reembolso':
        recibos = recibos.filter(devuelto_al_empleado=False, estado='activo') 
    elif estado_sel == 'pendiente_cobro':
        recibos = recibos.filter(asumido_por_cliente=True, cliente__isnull=False, cobrado_al_cliente=False, estado='activo') 
    elif estado_sel == 'completados':
        recibos = recibos.filter(devuelto_al_empleado=True, cobrado_al_cliente=True, estado='activo')
    
    empleados_db = ReciboCajaChica.objects.values_list('tercero_nombre', flat=True).distinct().exclude(tercero_nombre__isnull=True).exclude(tercero_nombre='')
    clientes = Cliente.objects.all()
    
    total_pend_reembolso = recibos.filter(devuelto_al_empleado=False, estado='activo').aggregate(Sum('total_pagado'))['total_pagado__sum'] or 0
    total_pend_cobro = recibos.filter(asumido_por_cliente=True, cobrado_al_cliente=False, estado='activo').aggregate(Sum('total_pagado'))['total_pagado__sum'] or 0

    reembolsos = ReembolsoEmpleado.objects.all().order_by('-id')
    cartas = CartaCobro.objects.select_related('cliente', 'correspondencia').all().order_by('-id')
    total_reembolsos_global = sum(r.total_reembolsado for r in reembolsos)
    total_cartas_global = sum(c.total_cobrar for c in cartas)
    
    documentos = []
    for r in reembolsos:
        documentos.append({
            'tipo': 'reembolso', 'id': r.id, 'numero': r.numero_reembolso, 
            'detalle': r.empleado_nombre, 'monto': r.total_reembolsado, 
            'url': f'/caja-chica/imprimir-reembolso/{r.id}/',
            'pagado': r.pagado
        })
    for c in cartas:
        nro_visible = f"{c.correspondencia.unidad_cites} {c.correspondencia.correlativo_completo}" if c.correspondencia else c.numero_carta
        documentos.append({
            'tipo': 'carta', 'id': c.id, 'numero': nro_visible, 
            'detalle': c.cliente.razon_social, 'monto': c.total_cobrar, 
            'url': f'/caja-chica/imprimir-carta/{c.id}/',
            'pagado': c.cobrado
        })
    documentos = sorted(documentos, key=lambda x: x['id'], reverse=True)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'generar_reembolso':
            recibos_ids = request.POST.getlist('recibos_seleccionados')
            empleado_nombre = request.POST.get('empleado_nombre')
            
            if recibos_ids and empleado_nombre:
                with transaction.atomic():
                    recibos_cobrar = ReciboCajaChica.objects.select_for_update().filter(id__in=recibos_ids, reembolso__isnull=True, estado='activo')
                    if recibos_cobrar.exists():
                        total = sum(r.total_pagado for r in recibos_cobrar)
                        ultimo = ReembolsoEmpleado.objects.order_by('-id').first()
                        max_seq = int(ultimo.numero_reembolso.split('-')[1]) if ultimo else 0
                        nuevo_num = f"REEM-{str(max_seq + 1).zfill(4)}"
                        
                        nuevo_reembolso = ReembolsoEmpleado.objects.create(
                            numero_reembolso=nuevo_num, empleado_nombre=empleado_nombre,
                            total_reembolsado=total, creado_por=request.user,
                            pagado=False
                        )
                        
                        for r in recibos_cobrar:
                            r.reembolso = nuevo_reembolso
                            r.save()
                            
                        messages.success(request, f"Planilla {nuevo_num} emitida. Confirma el pago al entregar el dinero.")
                        return redirect('imprimir_reembolso', reembolso_id=nuevo_reembolso.id)
            return redirect('control_gastos')

        elif form_type == 'generar_carta':
            recibos_ids = request.POST.getlist('recibos_seleccionados')
            cliente_id_post = request.POST.get('cliente_id')
            
            if recibos_ids and cliente_id_post:
                with transaction.atomic():
                    cliente = get_object_or_404(Cliente, id=cliente_id_post)
                    recibos_cobrar = ReciboCajaChica.objects.select_for_update().filter(
                        id__in=recibos_ids, carta_cobro__isnull=True, 
                        asumido_por_cliente=True, estado='activo'
                    )
                    
                    if recibos_cobrar.exists():
                        recibos_lista = list(recibos_cobrar)
                        total = sum(r.total_pagado for r in recibos_lista)
                        ultimo = CartaCobro.objects.order_by('-id').first()
                        max_seq = int(ultimo.numero_carta.split('-')[1]) if ultimo and ultimo.numero_carta else 0
                        nuevo_num = f"CC-{str(max_seq + 1).zfill(4)}"
                        
                        detalle_recibos = ", ".join(r.numero for r in recibos_lista if r.numero)
                        objeto_texto = f"Cobro de Gastos de Caja Chica ({detalle_recibos})" if detalle_recibos else "Cobro de Gastos de Caja Chica"

                        nueva_corresp = ControlCorrespondencia.objects.create(
                            tipo_carta='COBRO',
                            fecha=datetime.date.today(),
                            destino=cliente.razon_social,
                            nit=cliente.nit,
                            monto=total,
                            objeto=objeto_texto[:300]
                        )
                        
                        nueva_carta = CartaCobro.objects.create(
                            numero_carta=nuevo_num, 
                            cliente=cliente,
                            total_cobrar=total, 
                            creado_por=request.user,
                            correspondencia=nueva_corresp,
                            cobrado=False
                        )
                        
                        for r in recibos_lista:
                            r.carta_cobro = nueva_carta
                            r.save()
                            
                        messages.success(request, f"Carta emitida con correlativo {nueva_corresp.unidad_cites} {nueva_corresp.correlativo_completo}.")
                        return redirect('imprimir_carta', carta_id=nueva_carta.id)
            return redirect('control_gastos')

    return render(request, 'caja_chica/control_gastos.html', {
        'recibos': recibos, 'clientes': clientes, 'documentos': documentos,
        'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'cliente_id': cliente_id,
        'empleados_db': empleados_db, 'empleado_sel': empleado_sel, 'estado_sel': estado_sel,
        'total_reembolsos': total_reembolsos_global, 'total_cartas': total_cartas_global,
        'total_pend_reembolso': total_pend_reembolso, 'total_pend_cobro': total_pend_cobro,
    })

@login_required
def renumerar_recibos(request):
    if request.method == 'POST':
        f_inicio_str = request.POST.get('fecha_inicio')
        f_fin_str = request.POST.get('fecha_fin')
        
        if not f_inicio_str or not f_fin_str:
            messages.error(request, "Debes seleccionar ambas fechas para renumerar.")
            return redirect('control_gastos')

        try:
            f_inicio = datetime.datetime.strptime(f_inicio_str, '%d/%m/%Y').date()
            f_fin = datetime.datetime.strptime(f_fin_str, '%d/%m/%Y').date()
        except ValueError:
            messages.error(request, "Formato de fecha incorrecto. Use dd/mm/aaaa.")
            return redirect('control_gastos')

        with transaction.atomic():
            recibos_anteriores = ReciboCajaChica.objects.filter(fecha__lt=f_inicio)
            max_seq_anterior = 0
            for r in recibos_anteriores:
                try:
                    seq = int(r.numero.split('-')[1])
                    if seq > max_seq_anterior: max_seq_anterior = seq
                except Exception: pass

            condicion_bloqueados = Q(estado='anulado') | Q(solicitud__isnull=False, solicitud__estado='rendida')
            recibos_bloqueados = ReciboCajaChica.objects.filter(condicion_bloqueados, fecha__gte=f_inicio, fecha__lte=f_fin)
            numeros_bloqueados = []
            for r in recibos_bloqueados:
                try: numeros_bloqueados.append(int(r.numero.split('-')[1]))
                except Exception: pass

            condicion_libres = ~condicion_bloqueados
            recibos_libres = list(ReciboCajaChica.objects.filter(condicion_libres, fecha__gte=f_inicio, fecha__lte=f_fin).order_by('fecha', 'id'))

            if not recibos_libres:
                messages.warning(request, "No hay recibos elegibles para renumerar en este rango de fechas.")
                return redirect('control_gastos')

            for r in recibos_libres:
                r.numero = f"TMP-{r.id}"
                r.save()

            siguiente_seq = max_seq_anterior + 1
            contador = 0
            
            for r in recibos_libres:
                while siguiente_seq in numeros_bloqueados:
                    siguiente_seq += 1
                
                r.numero = f"REC-{str(siguiente_seq).zfill(5)}"
                r.save()
                siguiente_seq += 1
                contador += 1

            messages.success(request, f"¡Éxito! Se renumeraron {contador} recibos libres entre {f_inicio_str} y {f_fin_str}.")
    return redirect('control_gastos')

@login_required
def revertir_reembolso(request, reembolso_id):
    reembolso = get_object_or_404(ReembolsoEmpleado, id=reembolso_id)
    with transaction.atomic():
        ReciboCajaChica.objects.filter(reembolso=reembolso).update(
            devuelto_al_empleado=False, fecha_devolucion=None, reembolso=None
        )
        reembolso.delete()
    messages.warning(request, f"El reembolso fue revertido. Los recibos vuelven a estar pendientes.")
    return redirect('control_gastos')

@login_required
def revertir_carta(request, carta_id):
    carta = get_object_or_404(CartaCobro, id=carta_id)
    with transaction.atomic():
        if carta.correspondencia:
            carta.correspondencia.delete()
        ReciboCajaChica.objects.filter(carta_cobro=carta).update(
            cobrado_al_cliente=False, fecha_cobro=None, carta_cobro=None
        )
        carta.delete()
    messages.warning(request, f"La carta de cobro fue revertida. Los recibos vuelven a estar pendientes.")
    return redirect('control_gastos')

@login_required
def desanular_recibo(request, recibo_id):
    recibo = get_object_or_404(ReciboCajaChica, id=recibo_id)
    if recibo.devuelto_al_empleado or recibo.cobrado_al_cliente:
        messages.error(request, "No se puede desanular un recibo que ya fue reembolsado o cobrado.")
    else:
        recibo.estado = 'activo'
        recibo.save()
        messages.success(request, f"El recibo {recibo.numero} ha sido reactivado correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'control_gastos'))

@login_required
def confirmar_pago_reembolso(request, reembolso_id):
    reembolso = get_object_or_404(ReembolsoEmpleado, id=reembolso_id)
    if not reembolso.pagado:
        with transaction.atomic():
            reembolso.pagado = True
            reembolso.fecha_pago = datetime.date.today()
            reembolso.save()
            ReciboCajaChica.objects.filter(reembolso=reembolso).update(
                devuelto_al_empleado=True, fecha_devolucion=datetime.date.today()
            )
            messages.success(request, f"¡Reembolso {reembolso.numero_reembolso} PAGADO exitosamente!")
    return redirect('control_gastos')

@login_required
def confirmar_pago_carta(request, carta_id):
    carta = get_object_or_404(CartaCobro, id=carta_id)
    if not carta.cobrado:
        with transaction.atomic():
            carta.cobrado = True
            carta.fecha_pago = datetime.date.today()
            carta.save()
            ReciboCajaChica.objects.filter(carta_cobro=carta).update(
                cobrado_al_cliente=True, fecha_cobro=datetime.date.today()
            )
            messages.success(request, f"¡Carta de Cobro {carta.numero_carta} COBRADA exitosamente!")
    return redirect('control_gastos')

@login_required
def desmarcar_pago_reembolso(request, reembolso_id):
    reembolso = get_object_or_404(ReembolsoEmpleado, id=reembolso_id)
    if reembolso.pagado:
        with transaction.atomic():
            reembolso.pagado = False
            reembolso.fecha_pago = None
            reembolso.save()
            ReciboCajaChica.objects.filter(reembolso=reembolso).update(
                devuelto_al_empleado=False, fecha_devolucion=None
            )
            messages.warning(request, f"Se desmarcó el pago del Reembolso {reembolso.numero_reembolso}.")
    return redirect('control_gastos')

@login_required
def desmarcar_pago_carta(request, carta_id):
    carta = get_object_or_404(CartaCobro, id=carta_id)
    if carta.cobrado:
        with transaction.atomic():
            carta.cobrado = False
            carta.fecha_pago = None
            carta.save()
            ReciboCajaChica.objects.filter(carta_cobro=carta).update(
                cobrado_al_cliente=False, fecha_cobro=None
            )
            messages.warning(request, f"Se desmarcó el cobro de la Carta {carta.numero_carta}.")
    return redirect('control_gastos')

@login_required
def historial_reembolsos(request):
    reembolsos = ReembolsoEmpleado.objects.all().order_by('-id')
    reembolso_id = request.GET.get('id')
    reembolso_editar = None
    if reembolso_id:
        reembolso_editar = get_object_or_404(ReembolsoEmpleado, id=reembolso_id)

    return render(request, 'caja_chica/historial_reembolsos.html', {
        'reembolsos': reembolsos, 'reembolso_editar': reembolso_editar
    })

@login_required
def imprimir_reembolso(request, reembolso_id):
    reembolso = get_object_or_404(ReembolsoEmpleado, id=reembolso_id)
    recibos = ReciboCajaChica.objects.filter(reembolso=reembolso, estado='activo')
    total_real = sum(r.total_pagado for r in recibos)
    if total_real != reembolso.total_reembolsado:
        reembolso.total_reembolsado = total_real
        reembolso.save()
    return render(request, 'caja_chica/imprimir_reembolso.html', {
        'reembolso': reembolso, 'recibos': recibos, 'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0]
    })

@login_required
def rendicion_fondos(request):
    solicitudes_db = SolicitudCajaChica.objects.all().order_by('-id')
    sol_id = request.GET.get('id_sol')
    
    solicitudes = []
    for sol in solicitudes_db:
        recibos_sol = ReciboCajaChica.objects.filter(solicitud=sol)
        total_gastado_sol = sum((r.total_pagado for r in recibos_sol), Decimal('0.00'))
        total_disponible_sol = sol.importe_solicitado + sol.saldo_anterior + sol.prestamo_tercero
        saldo_actual = total_disponible_sol - total_gastado_sol
        if sol.estado == 'rendida':
            saldo_actual = sol.saldo_final
            
        sol.total_gastado = total_gastado_sol
        sol.saldo_actual = saldo_actual
        solicitudes.append(sol)

    solicitud_sel = None
    recibos_vinculados = []
    total_gastado = Decimal('0.00')
    saldo = Decimal('0.00')
    
    if sol_id:
        solicitud_sel = get_object_or_404(SolicitudCajaChica, id=sol_id)
        recibos_vinculados = ReciboCajaChica.objects.filter(solicitud=solicitud_sel).order_by('fecha')
        total_gastado = sum((r.total_pagado for r in recibos_vinculados), Decimal('0.00'))
        total_disponible = solicitud_sel.importe_solicitado + solicitud_sel.saldo_anterior + solicitud_sel.prestamo_tercero
        saldo = total_disponible - total_gastado

    if request.method == 'POST' and request.POST.get('form_type') == 'guardar_nombres':
        if solicitud_sel:
            solicitud_sel.rendido_de = request.POST.get('rendido_de')
            solicitud_sel.rendido_a = request.POST.get('rendido_a')
            solicitud_sel.prestamo_tercero = clean_decimal(request.POST.get('prestamo_tercero', '0'))
            solicitud_sel.save()
            messages.success(request, "Datos de la rendición actualizados.")
        return redirect(f'/caja-chica/rendicion/?id_sol={sol_id}')

    return render(request, 'caja_chica/rendicion_fondos.html', {
        'solicitudes': solicitudes, 'solicitud_sel': solicitud_sel,
        'recibos_vinculados': recibos_vinculados, 'total_gastado': total_gastado,
        'saldo': saldo, 'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0]
    })

@login_required
def imprimir_rendicion_completa(request, sol_id):
    solicitud = get_object_or_404(SolicitudCajaChica, id=sol_id)
    recibos = ReciboCajaChica.objects.filter(solicitud=solicitud).order_by('fecha')
    total_gastado = sum((r.total_pagado for r in recibos), Decimal('0.00'))
    total_disponible = solicitud.importe_solicitado + solicitud.saldo_anterior + solicitud.prestamo_tercero
    saldo = solicitud.saldo_final if solicitud.estado == 'rendida' else (total_disponible - total_gastado)

    return render(request, 'caja_chica/print_rendicion_completa.html', {
        'solicitud': solicitud,
        'recibos': recibos,
        'total_gastado': total_gastado,
        'saldo': saldo,
        'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0],
        'fecha_actual': datetime.date.today()
    })

@login_required
def vincular_recibos(request, sol_id):
    solicitud = get_object_or_404(SolicitudCajaChica, id=sol_id)
    if solicitud.estado == 'rendida':
        messages.error(request, "Esta solicitud ya está cerrada.")
        return redirect(f'/caja-chica/rendicion/?id_sol={solicitud.id}')
        
    todos_recibos = ReciboCajaChica.objects.all().order_by('-fecha')
    recibos_vinculados = ReciboCajaChica.objects.filter(solicitud=solicitud).order_by('-fecha')
    
    if request.method == 'POST':
        recibo_id = request.POST.get('recibo_id')
        accion = request.POST.get('accion')
        if recibo_id:
            recibo = get_object_or_404(ReciboCajaChica, id=recibo_id)
            with transaction.atomic():
                if accion == 'vincular': recibo.solicitud = solicitud
                elif accion == 'desvincular': recibo.solicitud = None
                recibo.save()
        return redirect(f'/caja-chica/rendicion/vincular/{solicitud.id}/')

    return render(request, 'caja_chica/vincular_recibos.html', {
        'solicitud': solicitud, 'recibos_vinculados': recibos_vinculados, 'todos_recibos': todos_recibos
    })

@login_required
def desvincular_recibo(request, rec_id):
    recibo = get_object_or_404(ReciboCajaChica, id=rec_id)
    if recibo.solicitud and recibo.solicitud.estado == 'abierta':
        sol_id = recibo.solicitud.id
        recibo.solicitud = None
        recibo.save()
        messages.success(request, f"Recibo {recibo.numero} desvinculado.")
        return redirect(f'/caja-chica/rendicion/vincular/{sol_id}/')
    else:
        messages.error(request, "No se puede desvincular de una rendición cerrada.")
        return redirect('rendicion_fondos')

@login_required
def cerrar_rendicion(request, sol_id):
    solicitud = get_object_or_404(SolicitudCajaChica, id=sol_id)
    if request.method == 'POST' and solicitud.estado == 'abierta':
        with transaction.atomic():
            recibos = ReciboCajaChica.objects.filter(solicitud=solicitud)
            total_gastado = sum(r.total_pagado for r in recibos)
            total_disponible = float(solicitud.importe_solicitado) + float(solicitud.saldo_anterior) + float(solicitud.prestamo_tercero)
            saldo_final = total_disponible - float(total_gastado)
            
            solicitud.saldo_final = saldo_final if saldo_final > 0 else 0 
            solicitud.estado = 'rendida'
            solicitud.save()
            messages.success(request, f"Rendición cerrada. Saldo a favor para el próximo periodo: Bs. {solicitud.saldo_final}")
        return redirect('rendicion_fondos')
    return redirect(f'/caja-chica/rendicion/?id_sol={solicitud.id}')

@login_required
def revertir_rendicion(request, sol_id):
    solicitud = get_object_or_404(SolicitudCajaChica, id=sol_id)
    if solicitud.estado == 'rendida':
        with transaction.atomic():
            solicitud.estado = 'abierta'
            solicitud.saldo_final = 0
            solicitud.save()
            messages.warning(request, f"La rendición {solicitud.numero_solicitud} ha sido REVERTIDA a estado ABIERTO.")
    return redirect(f'/caja-chica/rendicion/?id_sol={solicitud.id}')

@login_required
def cartas_cobro_dashboard(request, carta_id=None):
    cartas = CartaCobro.objects.select_related('cliente', 'correspondencia').all().order_by('-id')
    carta_sel = None
    recibos = []
    cliente = None
    fecha_formateada = ""
    correlativo_carta = ""

    if carta_id:
        carta_sel = get_object_or_404(CartaCobro, id=carta_id)
        recibos = ReciboCajaChica.objects.filter(carta_cobro=carta_sel).order_by('fecha', 'id')
        cliente = carta_sel.cliente
        
        f = carta_sel.correspondencia.fecha if carta_sel.correspondencia else carta_sel.fecha_emision
        fecha_formateada = f"Santa Cruz de la Sierra, {f.day} de {MESES_ES[f.month]} del {f.year}"

        if carta_sel.correspondencia:
            correlativo_carta = f"{carta_sel.correspondencia.unidad_cites} {carta_sel.correspondencia.correlativo_completo}"
        else:
            correlativo_carta = carta_sel.numero_carta or ""

    return render(request, 'caja_chica/carta_cobro.html', {
        'cartas': cartas,
        'carta': carta_sel,
        'recibos': recibos,
        'cliente': cliente,
        'fecha_formateada': fecha_formateada,
        'correlativo_carta': correlativo_carta,
        'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0]
    })

@login_required
def imprimir_recibo_pdf(request, recibo_id, tipo):
    recibo = get_object_or_404(ReciboCajaChica, id=recibo_id)
    copias = []

    if tipo == 'orig_copia':
        copias = [{'recibo': recibo, 'etiqueta': 'ORIGINAL'}, {'recibo': recibo, 'etiqueta': 'COPIA'}]
    elif tipo == 'lote':
        siguiente = ReciboCajaChica.objects.filter(id__gt=recibo.id).order_by('id').first()
        copias = [{'recibo': recibo, 'etiqueta': 'ORIGINAL'}]
        if siguiente: copias.append({'recibo': siguiente, 'etiqueta': 'ORIGINAL'})
        else: copias.append({'recibo': None, 'etiqueta': 'SIGUIENTE'})

    return render(request, 'caja_chica/print_recibo.html', {
        'copias': copias, 'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0]
    })

@login_required
def imprimir_recibo_rango(request):
    inicio = request.GET.get('inicio')
    fin = request.GET.get('fin')
    modo = request.GET.get('modo', 'correlativo')
    
    try:
        def formatear_numero(num):
            num_str = str(num).strip().upper()
            if num_str.startswith('REC-'):
                partes = num_str.split('-')
                if len(partes) == 2: return f"REC-{str(int(partes[1])).zfill(5)}"
            return f"REC-{str(int(num_str)).zfill(5)}"

        num_inicio = formatear_numero(inicio)
        num_fin = formatear_numero(fin)
        
        recibos = ReciboCajaChica.objects.filter(numero__gte=num_inicio, numero__lte=num_fin).order_by('numero')
        
        copias = []
        if modo == 'orig_copia':
            for recibo in recibos:
                copias.append({'recibo': recibo, 'etiqueta': 'ORIGINAL'})
                copias.append({'recibo': recibo, 'etiqueta': 'COPIA'})
        else:
            for recibo in recibos:
                copias.append({'recibo': recibo, 'etiqueta': 'ORIGINAL'})
                
        if not copias:
            messages.warning(request, f"No se encontraron recibos en el rango {inicio} al {fin}.")
            return redirect('caja_chica_dashboard')

        return render(request, 'caja_chica/print_recibo.html', {
            'copias': copias, 'config_empresa': ConfiguracionEmpresa.objects.get_or_create(id=1)[0]
        })
    except (ValueError, TypeError):
        messages.error(request, "Rango de números inválido.")
        return redirect('caja_chica_dashboard')

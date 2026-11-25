from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def lista_usuarios(request):
    # Traemos a todos los usuarios ordenados alfabéticamente
    usuarios = User.objects.all().order_by('username')
    return render(request, 'lista_usuarios.html', {'usuarios': usuarios})

@login_required
def crear_editar_usuario(request, user_id=None):
    usuario_editar = None
    if user_id:
        usuario_editar = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '') # 🔥 NUEVO
        last_name = request.POST.get('last_name', '')   # 🔥 NUEVO
        is_active = 'is_active' in request.POST

        if not usuario_editar and User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
            return redirect('crear_editar_usuario')

        if usuario_editar:
            usuario_editar.username = username
            usuario_editar.email = email
            usuario_editar.first_name = first_name # 🔥 NUEVO
            usuario_editar.last_name = last_name   # 🔥 NUEVO
            usuario_editar.is_active = is_active
            
            if password and password.strip() != "":
                usuario_editar.set_password(password)
                
            usuario_editar.save()
            messages.success(request, f'Usuario {username} actualizado correctamente.')
        else:
            nuevo_usuario = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name, # 🔥 NUEVO
                last_name=last_name    # 🔥 NUEVO
            )
            nuevo_usuario.is_active = is_active
            nuevo_usuario.save()
            messages.success(request, f'Usuario {username} creado correctamente.')

        return redirect('lista_usuarios')

    return render(request, 'formulario_usuario.html', {'usuario': usuario_editar})

@login_required
def toggle_usuario(request, user_id):
    # Función para habilitar o deshabilitar un usuario de un solo clic
    usuario = get_object_or_404(User, id=user_id)
    
    # Evitar que el usuario logueado se deshabilite a sí mismo
    if usuario == request.user:
        messages.error(request, 'No puedes deshabilitar tu propia cuenta.')
    else:
        usuario.is_active = not usuario.is_active
        usuario.save()
        estado = "habilitado" if usuario.is_active else "deshabilitado"
        messages.success(request, f'El usuario {usuario.username} ha sido {estado}.')
        
    return redirect('lista_usuarios')
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Debe decir exactamente 'inicio.html'
    return render(request, 'inicio.html') 
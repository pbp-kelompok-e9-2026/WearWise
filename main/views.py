from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect

# Main

def show_main(request):
    context = {
        'app_name': 'WearWise',
        'name': request.user.username if request.user.is_authenticated else 'Pengunjung',
    }
    return render(request, "index.html", context)

# Authentication

def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat. Silahkan login.")
        return redirect("main:login")
    return render(request, "main/register.html", {"form": form})

def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("main:home")
    return render(request, "main/login.html", {"form": form})

def logout_user(request):
    logout(request)
    return redirect("main:login")
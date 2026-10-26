from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

# Main

def show_main(request):
    return render(request, "main/home.html")

def about(request):
    return render(request, "main/about.html")

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
        return redirect(request.GET.get("next") or "main:show_main")
    return render(request, "main/login.html", {"form": form})

@require_POST
def logout_user(request):
    logout(request)
    return redirect("main:login")
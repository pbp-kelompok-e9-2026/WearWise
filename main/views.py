from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from worth_to_buy_analyzer.roles import is_analyzer, role_home

# Main

def show_main(request):
    if is_analyzer(request.user):
        return redirect(role_home(request.user))
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
        next_url = request.POST.get("next") or request.GET.get("next")
        safe_next = url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
        )
        workspace = reverse("worth_to_buy_analyzer:reference_list")
        if is_analyzer(request.user) and not request.user.is_superuser:
            # A stale user-page `next` must not send an Analyzer into the user flow.
            if not safe_next or not urlsplit(next_url).path.startswith(workspace):
                return redirect(role_home(request.user))
        return redirect(next_url if safe_next else role_home(request.user))
    return render(request, "main/login.html", {"form": form})

@require_POST
def logout_user(request):
    logout(request)
    return redirect("main:login")

"""Server-side roles; public registration always creates an ordinary user."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


ANALYZER_GROUP = "Analyzer"


def is_analyzer(user):
    return user.is_authenticated and user.groups.filter(name=ANALYZER_GROUP).exists()


def role_home(user):
    if user.is_superuser:
        return "admin:index"
    if is_analyzer(user):
        return "worth_to_buy_analyzer:reference_list"
    if user.is_staff:
        return "admin:index"
    return "main:show_main"


def analyzer_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_superuser or is_analyzer(request.user)):
            raise PermissionDenied("Halaman ini khusus akun Analyzer.")
        return view(request, *args, **kwargs)
    return wrapped


def purchase_user_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if is_analyzer(request.user) and not request.user.is_superuser:
            raise PermissionDenied("Gunakan ruang Analyzer untuk mengelola referensi pakaian.")
        return view(request, *args, **kwargs)
    return wrapped

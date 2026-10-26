from django.urls import path
from main import views

app_name = "main"

urlpatterns = [
    path("", views.show_main, name="show_main"),
    path("about/", views.about, name="about"),
    path("register/", views.register, name="register"),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
]
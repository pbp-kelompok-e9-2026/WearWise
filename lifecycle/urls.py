from django.urls import path

from . import views

app_name = "lifecycle"

urlpatterns = [
    path("", views.record_list, name="index"),
    path("create/", views.record_create, name="create"),
    path("<uuid:pk>/edit/", views.record_update, name="update"),
    path("<uuid:pk>/delete/", views.record_delete, name="delete"),
    path("json/", views.record_list_json, name="json"),
]
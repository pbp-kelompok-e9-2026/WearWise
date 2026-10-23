from django.urls import path

from . import views

app_name = "carbon_footprint"

urlpatterns = [
    path("", views.index, name="index"),
    path("estimates/", views.estimate_list, name="list"),
    path("estimates/new/", views.estimate_create, name="create"),
    path("estimates/<int:pk>/edit/", views.estimate_update, name="update"),
    path("estimates/<int:pk>/delete/", views.estimate_delete, name="delete"),
]

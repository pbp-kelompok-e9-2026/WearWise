from django.urls import path

from . import views

app_name = "carbon_footprint"

urlpatterns = [
    path("", views.index, name="index"),
    path("estimates/", views.estimate_list, name="list"),
    path("estimates/preview/", views.estimate_preview, name="preview"),
    path("estimates/new/", views.estimate_create, name="create"),
    path("estimates/<int:pk>/edit/", views.estimate_update, name="update"),
    path("analyzer/", views.analyzer, name="analyzer"),
    path("analyzer/factors/", views.factors, name="factors"),
    path("estimates/<int:pk>/delete/", views.estimate_delete, name="delete"),
]

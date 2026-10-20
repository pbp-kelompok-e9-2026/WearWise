from django.urls import path

from . import views

app_name = 'worth_to_buy_analyzer'

urlpatterns = [
    path('', views.analyzer, name='analyzer'),
]

from django.urls import path

from . import views

app_name = 'worth_to_buy_analyzer'

urlpatterns = [
    path('', views.analyzer, name='analyzer'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.update, name='update'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/decision/', views.decide, name='decide'),
    path('<int:pk>/refresh-carbon/', views.refresh_carbon, name='refresh_carbon'),
]

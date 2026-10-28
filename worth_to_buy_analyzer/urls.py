from django.urls import path

from . import reference_views, views

app_name = 'worth_to_buy_analyzer'

urlpatterns = [
    path('workspace/', reference_views.reference_list, name='reference_list'),
    path('workspace/new/', reference_views.reference_create, name='reference_create'),
    path('workspace/<int:pk>/', reference_views.reference_detail, name='reference_detail'),
    path('workspace/<int:pk>/edit/', reference_views.reference_update, name='reference_update'),
    path('workspace/<int:pk>/delete/', reference_views.reference_delete, name='reference_delete'),
    path('catalogue/', reference_views.catalogue, name='catalogue'),
    path('', views.analyzer, name='analyzer'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.update, name='update'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/decision/', views.decide, name='decide'),
    path('<int:pk>/refresh-carbon/', views.refresh_carbon, name='refresh_carbon'),
]

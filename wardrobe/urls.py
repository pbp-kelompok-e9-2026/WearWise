from django.urls import path
from . import views

app_name = 'wardrobe'

urlpatterns = [
    path('', views.show_wardrobe, name='show_wardrobe'),
    path('json/', views.get_wardrobe_json, name='get_wardrobe_json'),
    path('add-ajax/', views.add_clothing_ajax, name='add_clothing_ajax'),
    path('increment-wear/<uuid:item_id>/', views.increment_wear_ajax, name='increment_wear_ajax'),
    path('delete-ajax/<uuid:item_id>/', views.delete_clothing_ajax, name='delete_clothing_ajax'),
]
from django.urls import path
from dashboard.views import show_profile, register

app_name = 'dashboard'

urlpatterns = [
    path('', show_profile, name='show_profile'),
    path('register/', register, name='register'), 
]

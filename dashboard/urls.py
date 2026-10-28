from django.urls import path
from dashboard.views import show_profile, edit_profile, delete_account

app_name = 'dashboard'

urlpatterns = [
    path('profile/', show_profile, name='show_profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/delete/', delete_account, name='delete_account'),
]

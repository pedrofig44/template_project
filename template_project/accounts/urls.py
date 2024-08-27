from django.urls import path
from .views import login_view, register_view, logout

urlpatterns = [
    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout, name='logout'),
]


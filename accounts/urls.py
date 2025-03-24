from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import login_view, register_view, profile_view, reset_password_view, reset_password_validate_view, forgot_password_view, logout, about_us

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('logout/', logout, name='logout'),
    path('forgot_password/', forgot_password_view, name='forgot_password'),
    path('reset_password_validate/<uidb64>/<token>/', reset_password_validate_view, name='reset_password_validate'),
    path('reset_password/', reset_password_view, name='reset_password'),
    path('about-us/', about_us, name='about_us'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
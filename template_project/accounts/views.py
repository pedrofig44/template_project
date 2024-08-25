from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm

def login_view(request):
    return render(request, 'accounts/login.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after registration
            return redirect('main_dashboard')  # Redirect to profile or home page
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
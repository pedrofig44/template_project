from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages, auth
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

from .forms import CustomUserCreationForm, ProfileUpdateForm, ForgotPasswordForm
from .models import CustomUser

from accounts.utils import send_verification_email

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = auth.authenticate(username=username, password=password)
            if user is not None:
                auth.login(request, user)
                messages.success(request, f'Welcome, {username}!')
                return redirect('dashboard:main_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


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

@login_required
def profile_view(request):
    profile = request.user.profile  # Access the profile via the user's related_name

    if request.method == 'POST':
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')

    else:
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
    })

def logout(request):
    auth.logout(request)
    messages.info(request, 'Saíste da conta com sucesso.')
    return redirect('login')



def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            if CustomUser.objects.filter(email=email).exists():
                user = CustomUser.objects.get(email__exact=email)

                # Send reset password email using utility function
                mail_subject = 'Reset Your Password'
                email_template = 'accounts/emails/reset_password_email.html'
                send_verification_email(request, user, mail_subject, email_template)

                messages.success(request, 'Password reset link has been sent to your email address.')
                return redirect('forgot_password')
            else:
                messages.error(request, 'Account does not exist.')
                return redirect('forgot_password')
    else:
        form = ForgotPasswordForm()  # Show an empty form on GET request

    return render(request, 'accounts/forgot_password.html', {'form': form})

def reset_password_view(request):
    """
    This view allows the user to set a new password after validation.
    """
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            pk = request.session.get('uid')
            user = CustomUser.objects.get(pk=pk)
            user.set_password(password)
            user.is_active = True
            user.save()

            messages.success(request, 'Password reset successful.')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match!')
            return redirect('reset_password')
    return render(request, 'accounts/reset_password.html')


def reset_password_validate_view(request, uidb64, token):
    """
    This view validates the token for resetting the password and redirects the user to the reset form.
    """
    try:
        # Decode the base64 encoded user id (uidb64)
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        # Token is valid, proceed to reset password
        request.session['uid'] = uid  # Save the user ID in session for the reset_password view
        messages.info(request, 'Please reset your password.')
        return redirect('reset_password')  # Redirect to the password reset form
    else:
        # Token is invalid or expired
        messages.error(request, 'This link has expired!')
        return redirect('forgot_password')  # Redirect to the forgot password page


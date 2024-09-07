from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'organization']


    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.FREE_USER  # Set the default role
        if commit:
            user.save()
        return user
    
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'address', 'phone_number', 'profile_picture']

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
        return profile
    
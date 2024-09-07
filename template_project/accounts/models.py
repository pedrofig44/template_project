from django.contrib.auth.models import AbstractUser
from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    FREE_USER = 1
    PAID_USER = 2

    ROLE_CHOICES = (
        (FREE_USER, 'Free User'),
        (PAID_USER, 'Paid User'),
    )

    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=FREE_USER)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)

    def get_role(self):
        if self.role == self.FREE_USER:
            return 'Free User'
        elif self.role == self.PAID_USER:
            return 'Paid User'
        return 'Unknown Role'

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

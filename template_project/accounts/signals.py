from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile

# Signal to create a profile whenever a new CustomUser is created
@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

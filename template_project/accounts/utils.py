from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings

def send_verification_email(request, user, mail_subject, email_template):
    """
    Function to send a verification email for resetting password or account verification.
    """
    token = default_token_generator.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))  # Use 'uidb64'
    current_site = get_current_site(request)
    domain = current_site.domain

    message = render_to_string(email_template, {
        'user': user,
        'domain': domain,
        'uidb64': uidb64,
        'token': token,
    })

    send_mail(
        mail_subject,
        message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False,
    )

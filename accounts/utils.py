from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import UserNotification
from .tokens import email_verification_token

def notify_user(user, type, message, link=''):
    UserNotification.objects.create(recipient=user, type=type, message=message,link=link,)

def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # turned to bytes since urlsafe_base64_encode needs bytes not int - to encode the pk so its safe to put in the url

    #user_pk_bytes = force_bytes(UserModel._meta.pk.value_to_string(user))
    #uid = urlsafe_base64_encode(user_pk_bytes)
    token = email_verification_token.make_token(user)
    message = render_to_string('accounts/emails/verification_email.txt', {
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': request.get_host(),
        'uid': uid,
        'token': token,
    })
    send_mail('Потвърдете имейла си - WoolCraft', message, settings.DEFAULT_FROM_EMAIL, [user.email])

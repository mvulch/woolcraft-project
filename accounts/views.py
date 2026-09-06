from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, LogoutView
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_decode
from .forms import RegistrationForm, LoginForm
from .models import UserNotification
from .tokens import email_verification_token
from .utils import send_verification_email
from django.conf import settings

User = get_user_model()

# Create your views here.
def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(request, user)
            first_name = form.cleaned_data.get('first_name')
            messages.success(request, f"{first_name}, регистрацията Ви е успешна. "
                                       f"Изпратен е линк за потвърждение на акаунта.")
            return redirect('accounts:login')
    else:
        form = RegistrationForm()
        #print(form.errors)

    return render(request, "accounts/registration.html",{'form':form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
        # return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)

            if user is not None:
                if not user.email_verified:
                    resend_url = reverse('accounts:resend_verification')
                    messages.error(request, format_html(
                        'Моля, потвърдете имейл адреса си, преди да влезете. '
                        '<a href="{}">Изпратете нов линк за потвърждение</a>.', resend_url))
                else:
                    request.session['_old_session_key'] = request.session.session_key
                    login(request, user)
                    request.session.pop('cart_item_count', None)
                    # return redirect('accounts:profile')
                    return redirect('home')
            else:
                messages.error(request, "Грешен имейл или парола.")
        else:
            messages.error(request, "Невалиден формат на данни. Моля, опитайте отново.")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form':form})

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

class CustomLogoutView(LogoutView):
    next_page = 'home'

@login_required
def user_notifications_view(request):
    filter_read = request.GET.get('read', '')
    filter_type = request.GET.get('type', '')
    notifications = UserNotification.objects.filter(recipient=request.user)
    if filter_type:
        notifications = notifications.filter(type=filter_type)
    if filter_read == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_read == 'read':
        notifications = notifications.filter(is_read=True)
    paginator = Paginator(notifications, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'type_choices': UserNotification.Type.choices,
        'current_type': filter_type,
        'current_read': filter_read,
    }
    return render(request, 'accounts/notifications.html', context)

@login_required
def user_notification_is_read_view(request, notification_id):
    notification = get_object_or_404(UserNotification, id=notification_id, recipient=request.user)
    notification.is_read=True
    notification.save()
    if notification.link:
        return redirect(notification.link)
    return redirect('accounts:notifications')

def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        messages.success(request, 'Имейлът Ви е потвърден успешно. Вече можете да влезете.')
    else:
        messages.error(request, 'Линкът за потвърждение е невалиден или изтекъл.')
    return redirect('accounts:login')

def resend_verification_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.email_verified:
            send_verification_email(request, user)
        messages.success(request, 'Ако имейлът съществува и не е потвърден, изпратихме нов линк за потвърждение.')
        return redirect('accounts:login')
    return render(request, 'accounts/resend_verification.html')
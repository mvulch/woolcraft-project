from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from .models import Notification, NotificationRecipient
from django.contrib.auth.decorators import login_required
from django.http import Http404

superuser_required = user_passes_test(lambda u: u.is_active and u.is_superuser, login_url='accounts:login')

def staff_required(view_func):
    @login_required(login_url='accounts:login')
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper

def notify_staff(type, message, link='', exclude_user=None):
    """creates notification for the staff users when users trigger it"""
    User = get_user_model()
    staff_users = User.objects.filter(is_staff=True)
    if exclude_user is not None:
        staff_users = staff_users.exclude(pk=exclude_user.pk)
    notification = Notification.objects.create(
            type=type,
            message=message,
            link=link,
    )
    # bulk_create - only one sql query instead of N when N is the count of staff users
    NotificationRecipient.objects.bulk_create([
        NotificationRecipient(notification=notification, recipient=staff) for staff in staff_users
    ])
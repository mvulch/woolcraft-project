from django.urls import path, reverse_lazy
from .views import register_view, login_view, profile_view, CustomPasswordChangeView, CustomLogoutView, user_notifications_view, user_notification_is_read_view, verify_email_view, resend_verification_view
from django.contrib.auth import views as auth_views

app_name = 'accounts'
urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('profile/', profile_view, name='profile'),
    path('password-change/', CustomPasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/emails/password_reset_email.txt',
        success_url=reverse_lazy('accounts:password_reset_done')
    ),name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),

    path('password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),

    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    path('notifications/', user_notifications_view, name='notifications'),
    path('notification/<int:notification_id>/read/', user_notification_is_read_view, name='notification_read'),

    path('verify-email/<uidb64>/<token>/', verify_email_view, name='verify_email'),
    path('resend-verification/', resend_verification_view, name='resend_verification'),

]
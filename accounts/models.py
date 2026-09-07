from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True,blank=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    # so that auth system works with email not username
    USERNAME_FIELD = 'email'
    # fields that are asked for when creating superuser;
    # USERNAME_FIELD must not be included in REQUIRED_FIELDS as it is taken automatic
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

class UserNotification(models.Model):
    class Type(models.TextChoices):
        REVIEW_APPROVED = 'REVIEW_APPROVED', 'Одобрен отзив'
        REVIEW_DELETED = 'REVIEW_DELETED', 'Изтрит отзив'
        ORDER_STATUS = 'ORDER_STATUS', 'Статус на поръчка'
        CONTACT_REPLY = 'CONTACT_REPLY', 'Отговор на съобщение'
        CUSTOM_REQUEST_STATUS = 'CUSTOM_REQUEST_STATUS', 'Статус на персонализирана заявка'
        CUSTOM_REQUEST_PRICE = 'CUSTOM_REQUEST_PRICE', 'Предложена цена за заявка'
        CUSTOM_REQUEST_MESSAGE = 'CUSTOM_REQUEST_MESSAGE', 'Отговор на персонализирана заявка'
        STAFF_STATUS = 'STAFF_STATUS', 'Промяна на статус в екипа'
        COURSE_QUESTION_REPLY = 'COURSE_QUESTION_REPLY', 'Отговор на въпрос към урок'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_notifications')
    type = models.CharField(max_length=30, choices=Type.choices)
    message = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Известие към потребител'
        verbose_name_plural = 'Известия към потребители'

    def __str__(self):
        return f'{self.recipient.email} — {self.type}'
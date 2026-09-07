from django.db import models
from django.conf import settings

# Create your models here.
class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_ORDER = 'NEW_ORDER', 'Нова поръчка'
        NEW_REVIEW = 'NEW_REVIEW', 'Нов коментар'
        NEW_REQUEST = 'NEW_REQUEST', 'Нова заявка'
        NEW_CONTACT = 'NEW_CONTACT', 'Ново съобщение за контакт'
        NEW_COURSE_QUESTION = 'NEW_COURSE_QUESTION', 'Нов въпрос към урок'
    recipient = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='notifications', through='NotificationRecipient')
    type = models.CharField(max_length=20, choices=Type.choices)
    message = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Известие'
        verbose_name_plural = 'Известия'
    def __str__(self):
        return f'{self.type}'

class NotificationRecipient(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    class Meta:
        unique_together = ('notification', 'recipient')
        verbose_name = 'Известие към получател'
        verbose_name_plural = 'Известия към получатели'
    def __str__(self):
        return f'{self.recipient.email} - {self.notification.type}'
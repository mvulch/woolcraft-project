from django.db import models
from django.conf import settings
from orders.models import Address
from cloudinary.models import CloudinaryField
# Create your models here.
class CustomRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Чакаща'
        PRICE_OFFERED = 'PRICE_OFFERED', 'Предложена цена'
        PAID = 'PAID', 'Платена'
        COMPLETED = 'COMPLETED', 'Завършена'
        SHIPPED = "SHIPPED", "Изпратена"
        DELIVERED = "DELIVERED", "Доставена"
        REJECTED = 'REJECTED', 'Отказана от персонала'
        DECLINED = 'DECLINED', 'Отказана от клиента'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='custom_requests')
    title = models.CharField(max_length=100)
    description = models.TextField()
    specific_colors = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80)
    reference_image = CloudinaryField('Снимка от заявка', resource_type='image', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offered_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    stripe_payment_id = models.CharField(max_length=200, blank=True)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True, related_name='custom_requests')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Персонализирани заявки'
        verbose_name_plural = 'Персонализирани заявки'

    def __str__(self):
        return f'Заявка #{self.id} от {self.user.get_full_name()}'

class CustomRequestImage(models.Model):
    request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name='extra_images')
    image = CloudinaryField('Снимка от заявка', resource_type='image')
    class Meta:
        verbose_name = 'Снимка към заявка'
        verbose_name_plural = 'Снимки към заявки'
    def __str__(self):
        return f'Снимка за заявка #{self.request_id}'

class CustomRequestMessage(models.Model):
    request = models.ForeignKey(CustomRequest, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='custom_request_messages')
    text = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Съобщение към заявка'
        verbose_name_plural = 'Съобщения към заявки'
    def __str__(self):
        role = 'член на екипа' if self.user.is_staff else 'клиент'
        return f'Отговор от {role} {self.user.get_full_name()} на заявка #{self.request.id} за парсонализирана изработка.'
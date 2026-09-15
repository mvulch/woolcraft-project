from django.conf import settings
from django.db import models
from cloudinary.models import CloudinaryField

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=150)
    # category
    slug = models.SlugField(max_length=150, blank=False, unique=True)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="articles")
    def get_main_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Статия"
        verbose_name_plural = "Статии"
    def __str__(self):
        return self.title[:20]

class ArticleImage(models.Model):
    article = models.ForeignKey(Article,on_delete = models.CASCADE, related_name="images")
    image = CloudinaryField('Снимка на статия', resource_type='image', blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=120, blank=True)
    class Meta:
        verbose_name = "Изображение за статия"
        verbose_name_plural = "Изображения за статии"
    def __str__(self):
        return f"Image for {self.article.title}"

class ContactMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="message")
    subject = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Съобщение за контакт"
        verbose_name_plural = "Събощения за контакт"
    def __str__(self):
        status = "(Приключено)" if self.is_resolved else "(Незавършено)"
        return f"{status} събощение за контакт #{self.id} от {self.user.username}"

class ContactMessageReply(models.Model):
    message = models.ForeignKey(ContactMessage, on_delete=models.CASCADE, related_name="replies")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="message_replies")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']
        verbose_name = "Отговор на съобщение за контакт"
        verbose_name_plural = "Отговори на събощение за контакт"
    def __str__(self):
        role = "член на екипа" if self.user.is_staff else "клиент"
        return f"Отоговр от {role} {self.user.get_full_name()} на събощение за контакт #{self.message.id}"

class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,null=False, related_name="chat_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Чат сесия"
        verbose_name_plural = "Чат сесии"
    def __str__(self):
        return f"Session {self.id} - {self.user.email}"

class HeroSlide(models.Model):
    title = models.CharField(max_length=120, verbose_name='Заглавие')
    subtitle = models.CharField(max_length=200, blank=True, verbose_name='Подзаглавие')
    image = CloudinaryField('Снимка на банер', resource_type='image')
    button_text = models.CharField(max_length=40, blank=True, verbose_name='Текст на бутон')
    button_url = models.CharField(max_length=200, blank=True, verbose_name='Линк на бутон')
    order = models.PositiveIntegerField(default=1, verbose_name='Ред')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        ordering = ['order']
        verbose_name = 'Банер на начална страница'
        verbose_name_plural = 'Банери на начална страница'

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    chat_session = models.ForeignKey(ChatSession,on_delete=models.CASCADE, related_name="messages")
    text = models.TextField(blank=False)
    is_from_user = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "Чат съобщение"
        verbose_name_plural = "Чат съобщение"
    def __str__(self):
        sender = "Sender" if self.is_from_user else "Chat bot"
        return f"{sender}: {self.text[:20]}"
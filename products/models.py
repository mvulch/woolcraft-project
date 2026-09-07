from django.db import models
from django.conf import settings
from django.db.models import Avg
from cloudinary.models import CloudinaryField


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=120, blank=False,unique=True)
    description = models.TextField(blank=True)
    image = CloudinaryField('Снимка на категория', resource_type='image', blank=True, null=True)
    slug = models.SlugField(max_length=100, blank=False,unique=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,related_name="subcategories")

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=120, blank=False)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_products")
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, blank=False)
    slug = models.SlugField(max_length=100, blank=False,unique=True)

    def get_quantity_range(self):
        return range(1, self.stock_quantity + 1)

    def get_main_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    def get_average_rating(self):
        result = self.reviews.filter(is_published=True).aggregate(avg=Avg('rating'))
        avg = result['avg']
        return round(avg, 2) if avg else None

    def get_review_count(self):
        return self.reviews.filter(is_published=True).count()

    def get_url(self):
        from django.urls import reverse
        return reverse('products:product_detail', kwargs={'category_slug': self.category.slug, 'slug': self.slug})

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукти'

class ProductAttribute(models.Model):
    product = models.ForeignKey(Product,on_delete = models.CASCADE,related_name="attributes")
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"
    class Meta:
        verbose_name = 'Атрибут на продукт'
        verbose_name_plural = 'Атрибути на продукти'

class ProductImage(models.Model):
    product = models.ForeignKey(Product,on_delete = models.CASCADE, related_name="images")
    image = CloudinaryField('Снимка на продукт', resource_type='image', blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=120, blank=True)
    class Meta:
        verbose_name = 'Изображение за продукт'
        verbose_name_plural = 'Изображения за продукти'
    def __str__(self):
        return f"Image for {self.product.name}"

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    image = CloudinaryField('Снимка към отзив', resource_type='image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejection_count = models.PositiveIntegerField(default=0)
    class Meta:
        unique_together = ('user','product')
        ordering = ['-created_at']
        verbose_name = 'Ревю на продукт'
        verbose_name_plural = 'Ревюта на продукти'
    def __str__(self):
        return f'Review of {self.product.name} from {self.user.email}'

class VideoCourse(models.Model):

    class Difficulty(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name = "video_course")
    duration_minutes = models.PositiveIntegerField(blank=False)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices,default=Difficulty.BEGINNER)

    def get_progress_for_user(self, user):
        total = self.lessons.count()
        if not user or not user.is_authenticated or not total:
            return 0, total
        completed = LessonProgress.objects.filter(user=user, lesson__course=self, is_completed=True).count()
        return completed, total

    def __str__(self):
        return self.product.name
    class Meta:
        verbose_name = 'Видео курс'
        verbose_name_plural = 'Видео курсове'

class Lesson(models.Model):
    course = models.ForeignKey(VideoCourse, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=120)
    video = CloudinaryField('Видео на урок', resource_type='video', blank=True, null=True)
    order = models.PositiveIntegerField(default=1, verbose_name='Ред')
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    is_free_preview = models.BooleanField(default=False, verbose_name='Безплатен преглед')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроци'

    def get_url(self):
        from django.urls import reverse
        return reverse('products:course_watch_lesson', kwargs={'course_id': self.course_id, 'lesson_id': self.id})

    def __str__(self):
        return f'{self.course.product.name} - {self.title}'

class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_entries')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name = 'Прогрес на урок'
        verbose_name_plural = 'Прогрес на уроци'

    def __str__(self):
        return f'{self.user.email} - {self.lesson}'


class CourseQuestion(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_questions')
    text = models.TextField(max_length=1000, verbose_name='Въпрос')
    image = CloudinaryField('Снимка', resource_type='image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Въпрос към урок'
        verbose_name_plural = 'Въпроси към уроци'

    def __str__(self):
        return f'{self.user.email} - {self.lesson}'


class CourseQuestionReply(models.Model):
    question = models.ForeignKey(CourseQuestion, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_question_replies')
    text = models.TextField(max_length=1000, verbose_name='Отговор')
    image = CloudinaryField('Снимка', resource_type='image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Отговор на въпрос'
        verbose_name_plural = 'Отговори на въпроси'

    def __str__(self):
        return f'Reply by {self.user.email} to #{self.question_id}'
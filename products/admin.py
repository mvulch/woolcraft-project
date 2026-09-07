from django.contrib import admin
from .models import Category, Product, ProductAttribute, ProductImage, ProductReview, VideoCourse,Lesson, CourseQuestion, CourseQuestionReply
# Register your models here.
"""admin.site.register(Category)
    admin.site.register(Product)
    admin.site.register(ProductAttribute)
    admin.site.register(ProductImage)
    admin.site.register(VideoCourse)"""
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    search_fields =("name",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name","category", "price", "stock_quantity", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active", "category")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "value")
    search_fields = ("product__name", "name")

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "alt_text")
    list_filter = ("is_primary",)

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("is_published",)
    search_fileds = ("product__name","user__username",)
    readonly_fields = ("is_published", "is_rejected", "rejection_count")


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("title", "video", "order", "duration_minutes", "is_free_preview")

@admin.register(VideoCourse)
class VideoCourseAdmin(admin.ModelAdmin):
    list_display = ("product", "duration_minutes", "difficulty")
    list_filter = ("difficulty",)
    inlines = [LessonInline]

@admin.register(CourseQuestion)
class CourseQuestionAdmin(admin.ModelAdmin):
    list_display = ("lesson", "user", "created_at")
    search_fields = ("lesson__title", "user__email")

@admin.register(CourseQuestionReply)
class CourseQuestionReplyAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "created_at")
    search_fields = ("question__lesson__title", "user__email")


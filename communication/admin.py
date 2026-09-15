from django.contrib import admin
from .models import ChatSession, ChatMessage, ContactMessage, Article, ArticleImage, ContactMessageReply, HeroSlide
# Register your models here.
@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_filter = ("is_active",)
    list_editable = ("order", "is_active")

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at", "updated_at","author")
    search_fields = ("title", "created_at","author")
    list_filter = ("is_published",)
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(ArticleImage)
class ArticleImageAdmin(admin.ModelAdmin):
    list_display = ("article", "is_primary", "alt_text")
    list_filter = ("is_primary",)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "subject")
    search_fields = ("user__email", "subject")
    readonly_fields = ("created_at",)

@admin.register(ContactMessageReply)
class ContactMessageReplyAdmin(admin.ModelAdmin):
    list_display = ("message", "user")
    search_fields = ("user__email", "text", "message")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("user","started_at","last_activity_at")
    search_fields = ("user__email",)
    readonly_fields = ("started_at","last_activity_at")

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("chat_session","created_at","is_from_user")
    search_fields = ("text","chat_session__id")
    list_filter = ("is_from_user",)
    readonly_fields = ("created_at",)

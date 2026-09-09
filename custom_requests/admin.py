from django.contrib import admin
from .models import CustomRequest, CustomRequestImage, CustomRequestMessage

# Register your models here.
class CustomRequestImageInline(admin.TabularInline):
    model = CustomRequestImage
    extra = 0

@admin.register(CustomRequest)
class CustomRequestsAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_at', 'updated_at',)
    search_fields = ('title', 'user__email', 'description',)
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at','status','offered_price')
    inlines = [CustomRequestImageInline]

@admin.register(CustomRequestMessage)
class CustomRequestMessageAdmin(admin.ModelAdmin):
    list_display = ("request", "user")
    search_fields = ("user__email", "text", "request")
    readonly_fields = ("created_at",)
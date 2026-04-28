from django.contrib import admin
from administrator.models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active',)
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')

from django.contrib import admin
from .models import ECart

@admin.register(ECart)
class ECartAdmin(admin.ModelAdmin):
    list_display = ('id', 'ecart_id_num', 'created_at')
    search_fields = ('ecart_id_num',)
    ordering = ('created_at',)
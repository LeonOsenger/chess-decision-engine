from django.contrib import admin
from .models import ImportedGame


@admin.register(ImportedGame)
class ImportedGameAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'result', 'created_at')
    list_filter  = ('result',)
    search_fields = ('white', 'black', 'event')

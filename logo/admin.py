from django.contrib import admin
from .models import *
# Register your models here.

class CompanyLogoAdmin(admin.ModelAdmin):
    list_display = ['name','logo']
    search_fields=['name']
    class Meta:
        model=CompanyLogo
        
        
        
admin.site.register(CompanyLogo,CompanyLogoAdmin)
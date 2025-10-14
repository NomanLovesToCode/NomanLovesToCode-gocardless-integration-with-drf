from django.contrib import admin
from .models import *

# Register your models here.

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user','employment_status','job_details','employer','subscription_status','address_line1','city','country','postcode', 'created_at']
    search_fields = ['user__email']
    list_filter = ['employment_status','employer','subscription_status']
    ordering = ['-created_at','user__email']
    
    
    
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ['brand', 'brand_name', 'brand_sector', 'brand_owner', 'created_at']
    
    search_fields = ['brand_name', 'brand_website', 'brand_sector', 'brand_owner', 'brand_address_line1', 'brand_address_line2']
    
    
    
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(BrandProfile, BrandProfileAdmin)
from django.contrib import admin
from .models import *

# Register your models here.

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user','first_name', 'last_name','employment_status','job_details','employer','subscription_status','address_line1','city','country','postcode', 'created_at']
    search_fields = ['user__email', 'first_name', 'last_name']
    list_filter = ['employment_status','employer','subscription_status']
    ordering = ['-created_at','user__email']
    readonly_fields = ['mandate_id', 'customer_id']
    fieldsets = (
        
        (
            "Basic Information", {
                'fields':('user','profile_picture', 'first_name', 'last_name',)
            }
        ),
        
        (
            "Employment Details", {
                'fields': ('employment_status', 'job_details', 'employer')
            }
        ),
        
        (
            "Identification", {
                'fields': ('id_card_front', 'id_card_back')
            }
        ),
        
        (
            "User Address", {
                'fields': ('address_line1', 'address_line2', 'city', 'country', 'postcode')
            }
        ),
        
        (
            "User Subscription Status", {
                'fields': ('subscription_status', 'mandate_id', 'customer_id')
            }
        ),
        
    )
    
    
    
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ['brand', 'brand_name', 'brand_sector', 'brand_owner', 'created_at']
    
    search_fields = ['brand_name', 'brand_website', 'brand_sector', 'brand_owner', 'brand_address_line1', 'brand_address_line2']
    
    
    
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(BrandProfile, BrandProfileAdmin)
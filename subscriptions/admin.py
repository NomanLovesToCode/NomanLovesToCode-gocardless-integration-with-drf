from django.contrib import admin
from .models import *

# Register your models here.

#---------------------------
# Subscription Admin
#---------------------------

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'price', 'payment_id','subscription_id','status','is_active','created_at', 'started_at', 'expires_at']
    
    search_fields = ['user', 'payment_id', 'subscription_id','status']
    
    list_filter = ['is_active']
    
    
   
    
class PaymentHistoryAdmin(admin.ModelAdmin):
    fields = ['subscription', 'payment_id', 'amount', 'currency', 'status', 'charge_date', 'created_at', 'updated_at', 'gc_payment_id', 'gc_charge_date']
    
    readonly_fields = ['subscription', 'created_at', 'updated_at', 'gc_payment_id', 'gc_charge_date']
    
    list_display = ['subscription','payment_id', 'gc_payment_id', 'amount', 'currency','created_at','charge_date', 'status']
    
    search_fields = ['payment_id']
    
    list_filter = ['status']
    
    
    
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(PaymentHistory, PaymentHistoryAdmin)
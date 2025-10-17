from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.db.models.signals import post_save
from django.utils import timezone

from rest_framework import serializers

from accounts.models import *
from user_profile.models import BrandProfile
from datetime import timedelta
import secrets


@receiver(post_save, sender=User)
def create_mail_verification_signal(sender, instance, created, **kwargs):
    if created:
        token = secrets.token_hex(32)
        EmailVerification.objects.create(
            user=instance,
            token=token,
            expires_at= timezone.now()+timedelta(hours=1)
        )
        
        
        
# Admin creates user with role.brand for the BrandAccountRequest using brand request id
# and then approve the BrandAccountRequest 
# Brand profile creates automatically then using signals
@receiver(post_save, sender=BrandAccountRequest)
def create_brand_profile(sender, instance, created, **kwargs):
    if not created and instance.approved==True:
        instance_id = instance.brand_request_id
            
        user = get_object_or_404(User,brand_request_id = instance_id)
        
        brand_profile = BrandProfile.objects.get_or_create(brand=user)
        
        defaults = {
            'brand_name': instance.brand_name,  # Required field
            'brand_sector': instance.brand_sector or '',
            'brand_owner': instance.owner_name or '',  # Added: Set from request
            'brand_website': instance.website_link or None,
            'brand_address_line1': instance.address_line1 or '',  # Fixed: From instance, not user
            'brand_address_line2': instance.address_line2 or '',  # Fixed: From instance, not user
        }
        
        
        brand_profile, profile_created = BrandProfile.objects.get_or_create(
            brand=user,
            defaults=defaults
        )
        
        brand_profile, profile_created = BrandProfile.objects.get_or_create(
            brand=user,
            defaults=defaults
        )
        
        brand_profile.brand_sector = instance.brand_sector or brand_profile.brand_sector
        brand_profile.brand_owner = instance.owner_name or brand_profile.brand_owner
        brand_profile.brand_website = instance.website_link or brand_profile.brand_website
        brand_profile.brand_address_line1 = instance.address_line1 or brand_profile.brand_address_line1
        brand_profile.brand_address_line2 = instance.address_line2 or brand_profile.brand_address_line2
        
        
        brand_profile.save()
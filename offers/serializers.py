from datetime import timezone

from rest_framework import serializers
from .models import *

import logging

logger=logging.getLogger(__name__)



class OfferSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source="subcategory.subcategory_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = Offer
        fields = [
        'id', 'user_email', 'subcategory_name', 'brand_name','product', 'image', 'description', 'discount_percent', 'start_date', 'end_date', 'usage_type',
        'max_usage'
        ]
        read_only_fields = ["id", "user_email", "subcategory_name", "created_at"]


class SubCategorySerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = SubCategory
        fields = ["id", "category", "category_name", "subcategory_name","description", "offers"]
        read_only_fields = ["id", "category_name"]


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ["id", "category_name", "description", "subcategories"]
        read_only_fields = ["id"]
        
        
        
class VoucherSerializer(serializers.ModelSerializer):
    offer = OfferSerializer(read_only=True)
    claimed_by = serializers.CharField(source='claimed_by.email', read_only=True)
    
    class Meta:
        model = Voucher
        fields = [ 'id','offer','claimed_by', 'coupon', 'claimed', 'claimed_at' ]
        read_only_fields = ['id']
        
        

class VoucherReservationLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.email', read_only=True)
    voucher = VoucherSerializer(read_only=True)
    
    class Meta:
        model = VoucherReservationLog
        fields = [ 'id', 'user', 'voucher', 'claimed_at' ]
        read_only_fields = [ 'id', 'user', 'voucher' ]
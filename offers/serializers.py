from datetime import timezone

from rest_framework import serializers
from .models import Category, SubCategory, Offer

import logging

logger=logging.getLogger(__name__)



class OfferSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = Offer
        fields = [
        'id', 'brand_name','description', 'discount_percent', 'start_date', 'end_date', 'usage_type',
        'max_usage'
        ]
        read_only_fields = ["id", "user", "subcategory_name", "created_at"]


class SubCategorySerializer(serializers.ModelSerializer):
    # Use the correct related_name from the model
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
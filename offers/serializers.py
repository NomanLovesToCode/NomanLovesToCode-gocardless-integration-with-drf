# serializers.py
from rest_framework import serializers
from .models import Category, SubCategory, Offer


class OfferSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = Offer
        fields = [
            "id", "subcategory", "subcategory_name", "user", "user_email",
            "slug", "brand_name", "coupon_code", "description", 
            "discount_percent", "discount_amount", "start_date", "end_date", 
            "usage_type", "is_active", "max_uses", "minimum_purchase", 
            "created_at", "retailer_url"
        ]
        read_only_fields = ["id", "user", "user_email", "subcategory_name", "created_at"]


class SubCategorySerializer(serializers.ModelSerializer):
    # Use the correct related_name from the model
    products = OfferSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = SubCategory
        fields = ["id", "category", "category_name", "name", "slug", "description", "products"]
        read_only_fields = ["id", "category_name"]


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "subcategories"]
        read_only_fields = ["id"]
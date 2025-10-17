from rest_framework import serializers
from .models import *



class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'profile_picture', 'employment_status', 'job_details', 'employer', 'id_card_front', 
            'id_card_back', 'address_line1', 'address_line2', 'city', 'country', 'postcode'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'subscription_status']
    



class BasicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'profile_picture']
        read_only_fields = ['id', 'user', 'created_at', 'subscription_status']
    
    def validate_profile_picture(self, value):
        # Optional: Add validation for image size/type (e.g., < 5MB, JPG/PNG)
        if value:
            if value.size > 5 * 1024 * 1024:  # 5MB limit
                raise serializers.ValidationError("Profile picture size must be under 5MB.")
            if not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise serializers.ValidationError("Profile picture must be PNG or JPG.")
        return value
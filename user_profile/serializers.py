from rest_framework import serializers
from .models import *



class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'first_name','last_name','employment_status', 'job_details', 'employer', 'id_card_front', 'id_card_back', 'address_line1', 'address_line2', 'city', 'country', 'postcode'
        ]
        
        read_only_fields = ['id', 'user','created_at','subscription_status']
        
        
    def create(self, validated_data):
        user = self.context['request'].user
        if hasattr(user, 'profile'):
            raise serializers.ValidationError("Profile already exists for this user.")
        profile = UserProfile.objects.create(user=user, **validated_data)
        
        # if Payments.objects.get(user=user).exists():
        #     subscription = Payments.objects.get(user=user)
        #     if subcription.status == 'active':
        #         profile.subscription_status = True
        #     profile.save()
        return profile            
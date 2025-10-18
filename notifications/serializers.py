from rest_framework import serializers
from .models import MarketingCampaign
from accounts.models import User  # Corrected import

class MarketingCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingCampaign
        fields = '__all__'
        read_only_fields = ['status', 'sent_at', 'created_at']

class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone_no = serializers.CharField(max_length=18, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists() and not User.objects.get(email=value).subscribed:
            # Allow re-subscribe
            pass
        return value

class UnsubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        # Even if user doesn't exist, we can blacklist in Netcore
        return value
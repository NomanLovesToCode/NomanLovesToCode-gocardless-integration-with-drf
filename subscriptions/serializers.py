# subscriptions/serializers.py
from rest_framework import serializers
from rest_framework.validators import ValidationError
from .models import Subscription

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = '__all__'
        
        
class CreateCheckoutSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['active', 'cancelled', 'inactive', 'pending'])
    
    from rest_framework import serializers

class CreateMandateResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    billing_request_id = serializers.CharField()
    authorisation_url = serializers.URLField()
    
class CompleteMandateSerializer(serializers.Serializer):
    flow_token = serializers.CharField()
    status = serializers.CharField(required=False)  # For docs
    mandate_id = serializers.CharField(required=False)
    payment_id = serializers.CharField(required=False)
    subscription_id = serializers.CharField(required=False)
    message = serializers.CharField()

class CompleteBillingRequestSerializer(serializers.Serializer):
    status = serializers.CharField()
    status_url = serializers.CharField()
    message = serializers.CharField()

class MandateStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    mandate_id = serializers.CharField(required=False)
    customer_id = serializers.CharField(required=False)
    message = serializers.CharField()
    
class CancelMandateSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()

class PaymentResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    subscription_id = serializers.CharField()
    mandate_id = serializers.CharField()
    customer_id = serializers.CharField()
    next_charge_date = serializers.DateField(allow_null=True)

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
    
class CancelSubscriptionSerializer(serializers.Serializer):
    status = serializers.CharField()
    details = serializers.CharField()
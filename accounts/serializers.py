from django.contrib.auth import authenticate
from django.conf import settings
from django.utils import timezone  # Added if needed for validation timestamps

from rest_framework import serializers

from .tasks import verify_phone_number
from user_consent.consent_service import  UserConsentService
from user_profile.models import UserProfile
from notifications.marketing_service import MarketingPreferenceService
from user_consent.consent_service import UserConsentService
from notifications.marketing_service import MarketingPreferenceService


from .models import *

import logging
logger = logging.getLogger(__name__)

import re  # Added for password complexity

class RegistrationSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    agreed_to_terms_and_conditions = serializers.BooleanField(default=False)
    agreed_to_policy = serializers.BooleanField(default=False)
    agreed_to_sms_marketing = serializers.BooleanField(default=False)
    agreed_to_email_marketing = serializers.BooleanField(default=False)
    agreed_to_push_marketing = serializers.BooleanField(default=False)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'date_of_birth', 'phone_no',
            'agreed_to_terms_and_conditions', 'agreed_to_policy',
            'agreed_to_sms_marketing', 'agreed_to_email_marketing', 'agreed_to_push_marketing',
            'password', 'confirm_password'
        ]
        
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Password doesn't match")
        
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password is too small. At least 8 characters.")

        # Fixed: Handle async task properly (wait for result with .get(); fallback if timeout)
        phone_number = data["phone_no"]
        # try:
        #     task_result = verify_phone_number.delay(phone_number).get(timeout=10)  # Wait up to 10s
        #     if not task_result['valid']:
        #         raise serializers.ValidationError(task_result['error'])
        #     data["phone_no"] = task_result['formatted']  # Update with formatted number
        # except Exception as e:
        #     logger.warning(f"Phone validation timed out or failed: {e} - Skipping for now")
        #     # Fallback: Basic format check
        #     if not re.match(r'^\+?[\d\s-()]{10,15}$', phone_number):
        #         raise serializers.ValidationError("Invalid phone number format")
        
        # Added: Basic password complexity
        if not re.search(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', data['password']):
            raise serializers.ValidationError("Password must contain uppercase, lowercase, and number.")

        return data
        
    def create(self, validated_data):
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')
        # Extract user fields (exclude consents/marketing/password2)
        user_data = {
            k: v for k, v in validated_data.items()
            if k not in [
                'agreed_to_terms_and_conditions', 'agreed_to_policy',
                'agreed_to_sms_marketing', 'agreed_to_email_marketing', 'agreed_to_push_marketing',
                'confirm_password'
            ]
        }
        
        # Create user
        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()
        
        
        profile = UserProfile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name
            )
        
        profile.save()
        
        consent_data = {
            'agreed_to_terms_and_conditions': validated_data.get('agreed_to_terms_and_conditions'),
            'agreed_to_policy': validated_data.get('agreed_to_policy'),
            'agreed_to_sms_marketing': validated_data.get('agreed_to_sms_marketing'),
            'agreed_to_email_marketing': validated_data.get('agreed_to_email_marketing'),
            'agreed_to_push_notifications': validated_data.get('agreed_to_push_marketing'),  # Note: push_marketing → push_notifications
        }

        marketing_data = {
            'agreed_to_sms_marketing': validated_data.get('agreed_to_sms_marketing'),
            'agreed_to_email_marketing': validated_data.get('agreed_to_email_marketing'),
            'agreed_to_push_notifications': validated_data.get('agreed_to_push_marketing'),
        }
        MarketingPreferenceService.record_preference(user, **marketing_data)
        
        if not MarketingPreferenceService.validate_preferences_for_registration(**marketing_data)['success']: # Checkign whether the user has selected at least one marketing channel
            user.delete() # not letting open an account for not selecting a marketing channel by user deletion
            raise serializers.ValidationError ('You must select with at least one marketing preference')
        
        UserConsentService.record_consent(user, **consent_data)
        
        # Ensuring that users agree with terms & conditions, policies and at least one marketing method
        if not UserConsentService.validate_consent_for_registration(**consent_data)['success']: # Checkign whether the user has selected all the required consents
            user.delete()  # not letting open an account for not granting consents by user deletion
            raise serializers.ValidationError ('You must agree with the terms & conditions, and policies')
                
        

        
        logger.info(f'User : {user}')
        
        return user


class RegistrationResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, data):
        email = data["email"]
        password = data["password"]
        
        if email and password:
            user = authenticate(username=email, password=password)        
            logger.debug(f"Authentication attempt: {user}")
            if user:
                print(data)
                data["user"] = user
                print(data)
                
                return data
            else:
                raise serializers.ValidationError(
                    "Wrong login credentials!!!"
                )
        
        else:
            raise serializers.ValidationError(
                'Please enter your both email and password.'
            )


class LoginResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()


class ResendVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Password doesn't match")
        
        if len(data['new_password']) < 8:
            raise serializers.ValidationError("Password is too small. At least 8 characters. ")
        
        # Added: Same complexity as UserSerializer
        if not re.search(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', data['new_password']):
            raise serializers.ValidationError("Password must contain uppercase, lowercase, and number.")
        


class ForgetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):  # Fixed: Renamed from validate_mail to match field
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        return value 
    
    
class CheckResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    
    def validate(self, attrs):
        """
        Validate the reset code at the serializer level.
        This is more efficient than validating in both serializer and view.
        """
        email = attrs.get('email')
        code = attrs.get('code')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "email": "User with this email does not exist."
            })
            
        logger.info("Found the user for this email")
        
        try:
            reset_code = PasswordResetCode.objects.get(
                user=user, 
                code=code, 
                used=False
            )
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError({
                "code": "Invalid reset code."
            })
        
        logger.info("Found the model for this OTP")
        # Check if expired
        if not reset_code.is_valid():
            raise serializers.ValidationError({
                "code": "Reset code has expired. Please request a new one."
            })
            
        logger.info("OTP is valid")
        
        # Pass the reset_code object to validated_data for use in the view
        attrs['reset_code'] = reset_code
        attrs['user'] = user
        
        return attrs
    

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Password doesn't match")
        
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password is too small. At least 8 characters. ")
        
        # Added: Same complexity as UserSerializer
        if not re.search(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', data['password']):
            raise serializers.ValidationError("Password must contain uppercase, lowercase, and number.")
        
        
        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        
        return data
    
    
class BrandAccountRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAccountRequest
        fields = ['brand_name','brand_logo', 'brand_sector', 'website_link', 'owner_name', 'contact_email', 'contact_phone', 'contact_details','address_line1', 'address_line2', 'document']
        read_only_fields = ['id','brand_request_id', 'submitted_at'] 
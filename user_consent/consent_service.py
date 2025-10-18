from .models import UserConsent


class UserConsentService:
    """
    Service class for managing UserConsent records.
    Provides methods to create/update, retrieve, validate, and delete consent data.
    """
    
    @staticmethod
    def record_consent( user, agreed_to_terms_and_conditions=None, agreed_to_policy=None, agreed_to_sms_marketing=None, agreed_to_email_marketing=None, agreed_to_push_notifications=None ):
        # No raises here— just record. Validation moved to serializer.
        
        consent, _ = UserConsent.objects.get_or_create(user=user)
        
        if agreed_to_terms_and_conditions is not None:
            consent.agreed_to_terms_and_conditions = agreed_to_terms_and_conditions
        if agreed_to_policy is not None:
            consent.agreed_to_policy = agreed_to_policy
        if agreed_to_sms_marketing is not None:
            consent.agreed_to_sms_marketing = agreed_to_sms_marketing
        if agreed_to_email_marketing is not None:
            consent.agreed_to_email_marketing = agreed_to_email_marketing
        if agreed_to_push_notifications is not None:
            consent.agreed_to_push_notifications = agreed_to_push_notifications
        
        consent.save()
        
        # Return success dict for flexibility
        return {'success': True, 'consent': consent}
    
    
    @staticmethod
    def validate_consent_for_registration(agreed_to_terms_and_conditions=None, agreed_to_policy=None, agreed_to_sms_marketing=None, agreed_to_email_marketing=None, agreed_to_push_notifications=None):
        """
        Separate validation method—returns dict for caller to handle.
        """
        if not (agreed_to_terms_and_conditions == True and agreed_to_policy == True):
            return {'success': False, 'error': "You must agree with terms, conditions and policies to register"}
        
        if not any([agreed_to_sms_marketing == True, agreed_to_email_marketing == True, agreed_to_push_notifications == True]):
            return {'success': False, 'error': "You must agree with at least one marketing preference"}
        
        return {'success': True}
    
    
    @staticmethod
    def get_user_consent(user):
        try:
            return {'success': True, 'consent': UserConsent.objects.get(user=user)}
        except UserConsent.DoesNotExist:
            return {'success': False, 'error': 'No consent record found'}
        
        
    @staticmethod
    def delete_user_consent(user):
        try:
            consent = UserConsent.objects.get(user=user)
            consent.delete()
            return {'success': True}
        except UserConsent.DoesNotExist:
            return {'success': False, 'error': 'No consent record to delete'}
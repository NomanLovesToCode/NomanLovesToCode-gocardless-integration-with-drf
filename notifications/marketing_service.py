from .models import MarketingPreferences


class MarketingPreferenceService:
    
    @staticmethod
    def record_preference(
        user,
        agreed_to_sms_marketing=None,
        agreed_to_email_marketing=None,
        agreed_to_push_notifications=None
    ):
        # No raises—just record.
        marketing_preferences, _ = MarketingPreferences.objects.get_or_create(user=user)
        
        if agreed_to_sms_marketing is not None:
            marketing_preferences.sms = agreed_to_sms_marketing
        if agreed_to_email_marketing is not None:
            marketing_preferences.email = agreed_to_email_marketing
        if agreed_to_push_notifications is not None:
            marketing_preferences.push = agreed_to_push_notifications
        
        marketing_preferences.save()
        
        return {'success': True, 'preferences': marketing_preferences}
    

    @staticmethod   
    def validate_preferences_for_registration(agreed_to_sms_marketing=None, agreed_to_email_marketing=None, agreed_to_push_notifications=None):
        """
        Separate validation—returns dict.
        """
        if not any([agreed_to_sms_marketing == True, agreed_to_email_marketing == True, agreed_to_push_notifications == True]):
            
            return {'success': False, 'error': "You must agree to at least one marketing preference"}
        
        return {'success': True}
    
    
    @staticmethod
    def get_user_preferences(user):
        try:
            return {'success': True, 'preferences': MarketingPreferences.objects.get(user=user)}
        except MarketingPreferences.DoesNotExist:
            return {'success': False, 'error': 'No preferences record found'}
    
    @staticmethod
    def delete_user_preferences(user):
        try:
            preferences = MarketingPreferences.objects.get(user=user)
            preferences.delete()
            return {'success': True , 'details':"User's marketing preferences has been deleted"}
        except MarketingPreferences.DoesNotExist:
            return {'success': False, 'error': 'No preferences record to delete'}
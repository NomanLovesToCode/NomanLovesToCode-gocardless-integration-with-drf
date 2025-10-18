from django.db import models
from accounts.models import User

#user_consent.models


# Create your models here.
class UserConsent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_consent")
    agreed_to_terms_and_conditions = models.BooleanField(default=False)
    agreed_to_policy = models.BooleanField(default=False)
    agreed_to_sms_marketing = models.BooleanField(default=False)
    agreed_to_email_marketing = models.BooleanField(default=False)
    agreed_to_push_notifications = models.BooleanField(default=False)
    consent_date = models.DateTimeField(auto_now_add=True)
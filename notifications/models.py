from django.db import models
from django.utils import timezone
from accounts.models import User

#notifications.models

class MarketingCampaign(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="HTML or plain text content for the notification")
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('sending', 'Sending'),
            ('sent', 'Sent'),
            ('failed', 'Failed')
        ],
        default='scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}" 

    class Meta:
        ordering = ['-scheduled_at']


class NotificationLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.campaign.title} - {self.status}"

    class Meta:
        ordering = ['-sent_at']
        
        
class MarketingPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='marketing_preference')
    email = models.BooleanField(default=False)
    sms = models.BooleanField(default=False)
    push = models.BooleanField(default=False)
    
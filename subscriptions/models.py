# subscriptions/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
import secrets
import logging

logger = logging.getLogger(__name__)


class Subscription(models.Model):
    STATUS = [
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("inactive", "Inactive"),
        ("pending", "Pending"),
        ("expired", "Expired"),
    ]
      
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    price = models.DecimalField(decimal_places=2, max_digits=5, default=4.99)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    subscription_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    status = models.CharField(max_length=30, choices=STATUS, default="inactive")
    
    # Temporary fields for flow tracking
    temp_flow_id = models.CharField(max_length=100, blank=True, null=True)
    temp_billing_request_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    temp_state = models.CharField(max_length=64, blank=True, null=True)  # CSRF protection
    
    # Subscription lifecycle
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    last_payment_date = models.DateTimeField(null=True, blank=True)
    failed_payment_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Subscription for {self.user.email} - {self.status}"
    
    def is_valid(self):
        """Check if subscription is currently valid"""
        if not self.is_active:
            return False
        if self.expires_at is None:
            return False
        return self.expires_at > timezone.now()
    
    def days_until_expiry(self):
        """Get days remaining until expiry"""
        if self.expires_at is None:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    def mark_cancelled(self):
        """Mark subscription as cancelled"""
        self.is_active = False
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()
        logger.info(f"Subscription marked as cancelled for user {self.user.email}")
    
    def mark_expired(self):
        """Mark subscription as expired"""
        if self.is_valid():
            return  # Don't expire if still valid
        
        self.is_active = False
        self.status = 'expired'
        self.save()
        
        # Sync user flags
        self.user.subscription_status = False
        self.user.save()
        if hasattr(self.user, 'profile'):
            self.user.profile.subscription_status = False
            self.user.profile.save()
        
        logger.info(f"Subscription marked as expired for user {self.user.email}")
    
    def renew(self, next_charge_date=None):
        """Renew subscription after successful payment"""
        self.is_active = True
        self.status = 'active'
        self.last_payment_date = timezone.now()
        self.failed_payment_count = 0
        
        if next_charge_date:
            self.expires_at = next_charge_date
        else:
            self.expires_at = timezone.now() + timedelta(days=365)
        
        self.save()
        
        # Sync user flags
        self.user.subscription_status = True
        self.user.save()
        if hasattr(self.user, 'profile'):
            self.user.profile.subscription_status = True
            self.user.profile.save()
        
        logger.info(f"Subscription renewed for user {self.user.email} until {self.expires_at}")
    
    def record_failed_payment(self):
        """Record a failed payment attempt"""
        self.failed_payment_count += 1
        
        # After 3 failed payments, deactivate
        if self.failed_payment_count >= 3:
            self.is_active = False
            self.status = 'inactive'
            
            self.user.subscription_status = False
            self.user.save()
            if hasattr(self.user, 'profile'):
                self.user.profile.subscription_status = False
                self.user.profile.save()
            
            logger.warning(f"Subscription deactivated after {self.failed_payment_count} failed payments for {self.user.email}")
        
        self.save()
    
    def clear_temp_fields(self):
        """Clear temporary flow tracking fields"""
        self.temp_flow_id = None
        self.temp_billing_request_id = None
        self.temp_state = None
        self.save()
    
    def save(self, *args, **kwargs):
        # Auto-set price if not set
        if not self.price:
            self.price = 4.99
        
        # Generate payment_id only if it doesn't exist
        if self.payment_id is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.payment_id = f'PAYID-{self.user.id}-{timestamp}-{secrets.token_hex(4)}'
        
        # Set started_at on first activation
        if self.is_active and not self.started_at and self.status == 'active':
            self.started_at = timezone.now()
        
        # Auto-expire if past expiry date (ensure both are timezone-aware)
        if self.expires_at:
            # Make sure expires_at is timezone-aware
            if timezone.is_naive(self.expires_at):
                self.expires_at = timezone.make_aware(self.expires_at)
            
            # Now safe to compare
            if self.expires_at < timezone.now() and self.is_active:
                self.is_active = False
                self.status = 'expired'
                logger.info(f"Auto-expired subscription for {self.user.email}")
        
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['temp_billing_request_id']),
            models.Index(fields=['subscription_id']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'


class PaymentHistory(models.Model):
    """Track payment history for auditing"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payment_history')
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    currency = models.CharField(max_length=3, default='GBP')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS)
    charge_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # GoCardless specific
    gc_payment_id = models.CharField(max_length=100, blank=True, null=True)
    gc_charge_date = models.DateField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.status} - {self.subscription.user.email}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        indexes = [
            models.Index(fields=['gc_payment_id']),
            models.Index(fields=['status']),
        ]
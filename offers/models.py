# models.py
from django.utils.text import slugify
from django.utils import timezone
from django.db import models, transaction
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from accounts.models import User
import uuid
import secrets
import random
from datetime import timedelta


class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ["category_name"]
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    subcategory_name = models.CharField(max_length=50)
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ["subcategory_name"]
        unique_together = ("category", "subcategory_name")
        verbose_name = 'SubCategory'
        verbose_name_plural = 'SubCategories'

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class Offer(models.Model):
    SINGLE_USE = "single"
    MULTI_USE = "multi"

    USAGE_CHOICES = [
        (SINGLE_USE, "Single Use"),
        (MULTI_USE, "Multi Use"),
    ]
    
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="offers")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="offer_user")
    brand_name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, help_text="Optional: describe the offer")
    batch_size = models.PositiveIntegerField(
        default=1, 
        help_text="Number of unique vouchers to generate. Set to 1 if all codes should be the same."
    )
    discount_percent = models.PositiveIntegerField(blank=True, null=True)

    start_date = models.DateTimeField(help_text="Time and date from when the offer will begin")
    end_date = models.DateTimeField(help_text="Time and date until when the offer will be valid")
    usage_type = models.CharField(max_length=10, choices=USAGE_CHOICES, default=MULTI_USE)
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(
        null=True, blank=True, 
        help_text="Max total uses across all partners (null = unlimited)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    brand_url = models.URLField(help_text="External website where coupon can be used")
    auto_voucher_generation = models.BooleanField(
        default=False,
        help_text="Automatically generate vouchers after saving"
    )
    
    # New fields for user limitations
    max_vouchers_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Maximum vouchers a user can reserve from this offer"
    )
    voucher_cooldown_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours a user must wait before reserving another voucher (default: 24)"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand_name}"
    
    def save(self, *args, **kwargs):
        
        if self.prefix:
            self.prefix.upper()
        super().save(*args, **kwargs)
        
    def is_valid(self):
        """Check if offer is currently valid"""
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date
        )
    
    def clean(self):
        """Validate model fields"""
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
        if timezone.now() >= self.end_date:
            raise ValidationError("End date must be in the future")
        
        if self.discount_percent and (self.discount_percent < 0 or self.discount_percent > 100):
            raise ValidationError("Discount percent must be between 0 and 100")
    
    def generate_vouchers(self):
        """Generate unique voucher codes for this offer"""
        voucher_codes = []
        existing_codes = set(Voucher.objects.values_list('coupon', flat=True))
        
        attempts = 0
        max_attempts = self.batch_size * 10  # Prevent infinite loops
        
        while len(voucher_codes) < self.batch_size and attempts < max_attempts:
            attempts += 1
            random_length = random.randint(4, 16)
            code = f"{self.prefix}-{uuid.uuid4().hex[:8].upper()}-{secrets.token_hex(random_length).upper()}"
            
            # Ensure uniqueness
            if code not in existing_codes and code not in [v.coupon for v in voucher_codes]:
                voucher_codes.append(Voucher(offer=self, coupon=code))
        
        if len(voucher_codes) < self.batch_size:
            raise ValidationError(
                f"Could only generate {len(voucher_codes)} unique codes out of {self.batch_size} requested"
            )
        
        # Bulk create all vouchers
        with transaction.atomic():
            Voucher.objects.bulk_create(voucher_codes, batch_size=1000)
        
        return len(voucher_codes)
    
    def get_available_voucher_count(self):
        """Get count of unreserved vouchers"""
        return self.vouchers.filter(reserved_by__isnull=True).count()
    
    def get_total_uses(self):
        """Get total number of times vouchers have been used"""
        return self.vouchers.filter(is_seen=True).count()


class Voucher(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='vouchers')
    coupon = models.CharField(
        max_length=64, 
        unique=True,
        validators=[MinLengthValidator(8)]
    )
    is_seen = models.BooleanField(
        default=False,
        help_text="Has this voucher been revealed/used by a customer"
    )
    reserved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        related_name='reserved_vouchers',
        blank=True, 
        null=True,
        help_text="User who has reserved this voucher"
    )
    reserved_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When the voucher was reserved"
    )
    revealed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the voucher code was first revealed to the user"
    )
    
    class Meta:
        ordering = ['offer', 'coupon']
        verbose_name = 'Voucher Code'
        verbose_name_plural = 'Voucher Codes'
        indexes = [
            models.Index(fields=['offer', 'reserved_by']),
            models.Index(fields=['reserved_at']),
            models.Index(fields=['is_seen']),
        ]
        
    def __str__(self):
        status = 'used' if self.is_seen else ('reserved' if self.reserved_by else 'available')
        return f'{self.coupon} - {status}'
    
    def is_reservation_expired(self):
        """Check if reservation has expired"""
        if not self.reserved_at or not self.offer.reservation_expiry_minutes:
            return False
        
        expiry_time = self.reserved_at + timedelta(minutes=self.offer.reservation_expiry_minutes)
        return timezone.now() > expiry_time and not self.is_seen
    
    def release_if_expired(self):
        """Release reservation if expired and not used"""
        if self.is_reservation_expired():
            self.reserved_by = None
            self.reserved_at = None
            self.save(update_fields=['reserved_by', 'reserved_at'])
            return True
        return False


class VoucherReservationLog(models.Model):
    """Track user reservation history for enforcement of limits"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voucher_reservations')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='reservation_logs')
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='reservation_logs')
    reserved_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    was_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-reserved_at']
        indexes = [
            models.Index(fields=['user', 'offer', 'reserved_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.offer.brand_name} - {self.reserved_at}"
    
    @classmethod
    def can_user_reserve(cls, user, offer):
        """
        Check if user can reserve a voucher from this offer based on:
        1. Total vouchers reserved from this offer
        2. Cooldown period since last reservation
        """
        # Check total reservations (active + used)
        total_reservations = cls.objects.filter(
            user=user,
            offer=offer,
            released_at__isnull=True  # Only count non-released reservations
        ).count()
        
        if total_reservations >= offer.max_vouchers_per_user:
            return False, f"You've reached the maximum of {offer.max_vouchers_per_user} voucher(s) for this offer"
        
        # Check cooldown period
        if offer.voucher_cooldown_hours > 0:
            cooldown_threshold = timezone.now() - timedelta(hours=offer.voucher_cooldown_hours)
            recent_reservation = cls.objects.filter(
                user=user,
                offer=offer,
                reserved_at__gte=cooldown_threshold
            ).first()
            
            if recent_reservation:
                hours_left = offer.voucher_cooldown_hours - (
                    (timezone.now() - recent_reservation.reserved_at).total_seconds() / 3600
                )
                return False, f"Please wait {hours_left:.1f} more hour(s) before reserving another voucher"
        
        return True, "OK"
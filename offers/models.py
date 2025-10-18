# models.py
from django.utils.text import slugify
from django.utils import timezone
from django.db import models, transaction, IntegrityError
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from accounts.models import User
from datetime import timedelta
import uuid
import secrets
import random
import logging

logger = logging.getLogger(__name__)


class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.category_name


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
        return f"{self.category.category_name} → {self.subcategory_name}"


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
    product = models.CharField(max_length=264)
    image = models.ImageField(upload_to='offer_images/', blank=True, null=True)
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
    max_usage = models.PositiveIntegerField(
        null=True, blank=True, 
        help_text="Max total uses across all partners (null = unlimited)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    brand_url = models.URLField(help_text="External website where coupon can be used")
    auto_voucher_generation = models.BooleanField(
        default=False,
        help_text="If checked voucher(s) generate automatically. Otherwise, you must create Voucher for this offer manually,"
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
            self.prefix=self.prefix.upper()
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
        if self.end_date and timezone.now() >= self.end_date:
            raise ValidationError("End date must be in the future")
        
        if self.discount_percent and (self.discount_percent < 0 or self.discount_percent > 100):
            raise ValidationError("Discount percent must be between 0 and 100")
    
    def generate_vouchers(self):
        """Generate unique voucher codes for this offer"""
        voucher_codes = []
        for _ in range(self.batch_size):
            attempts = 0
            while attempts < 5:
                attempts += 1
                random_length = random.randint(4, 16)
                code = f"{self.prefix}-{uuid.uuid4().hex[:8].upper()}-{secrets.token_hex(random_length).upper()}"
                try:
                    with transaction.atomic():
                        voucher = Voucher(offer=self, coupon=code)
                        voucher.full_clean()  # Validate
                        voucher.save()
                        voucher_codes.append(voucher)
                        break
                except IntegrityError:
                    continue  # Retry
            if attempts == 5:
                logger.warning(f"Failed to generate unique code after 5 attempts")
        return len(voucher_codes)

class Voucher(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='vouchers')
    claimed_by = models.ForeignKey(User, on_delete=models.DO_NOTHING,blank=True, null=True, related_name='user')
    coupon = models.CharField(
        max_length=128, 
        unique=True,
        validators=[MinLengthValidator(8)]
    )
    claimed = models.BooleanField(
        default=False,
        help_text="Has this voucher been revealed/used by a customer"
    )
    claimed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the voucher code was first revealed to the user"
    )
    
    claimed_at.short_description = 'Voucher claimed at'
    claimed_by.short_description = 'Voucher claimed by'
    coupon.short_description = 'Coupon code'
    
    
    class Meta:
        ordering = ['offer', 'coupon']
        verbose_name = 'Voucher Code'
        verbose_name_plural = 'Voucher Codes'
        indexes = [
            models.Index(fields=['offer']),
            models.Index(fields=['claimed_at']),
            models.Index(fields=['claimed']),
        ]
        
    def __str__(self):
        status = 'used' if self.claimed else ('reserved' if self.claimed_by else 'available')
        return f'{self.coupon} - {status}'
    
    def is_eligible_for_new_voucher(self, user):
        if not self.claimed_by == user:
            return False
        cooldown_delta = timedelta(hours=self.offer.voucher_cooldown_hours)
        return timezone.now() >= (self.claimed_at + cooldown_delta)


class VoucherReservationLog(models.Model):
    """Track user reservation history for enforcement of limits"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voucher_reservations')
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='reservation_logs')
    claimed_at = models.DateTimeField(auto_now_add=True)
    
    claimed_at.short_description = 'Claimed at'
    
    class Meta:
        ordering = ['-claimed_at']
        unique_together = ("user", "voucher")
        indexes = [
            models.Index(fields=['user', 'voucher', 'claimed_at']),
        ]
        
        
    
    def __str__(self):
        return f"{self.user} claimed it on {self.claimed_at}"
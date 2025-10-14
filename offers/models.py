# models.py
from django.utils.text import slugify
from django.utils import timezone
from django.db import models
from accounts.models import User


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("category", "name")
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
    
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="products")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="offer_user")
    brand_name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True, help_text="Optional: describe the offer")
    discount_percent = models.PositiveIntegerField(blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_type = models.CharField(max_length=10, choices=USAGE_CHOICES, default=MULTI_USE)
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True, 
                                         help_text="Max total uses (null = unlimited)")
    minimum_purchase = models.DecimalField(max_digits=10, decimal_places=2, 
                                         null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    retailer_url = models.URLField(help_text="External website where coupon can be used")

    class Meta:
        ordering = ["brand_name"]

    def __str__(self):
        return f"{self.brand_name} - {self.coupon_code}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Create slug from brand_name and coupon_code
            self.slug = slugify(f"{self.brand_name}")
        super().save(*args, **kwargs)
        
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.start_date <= now <= self.end_date)
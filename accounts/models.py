from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
import secrets

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        if extra_fields.get("is_active") is not True:
            raise ValueError("Superuser must be is_active=True to act as an admin")
        if extra_fields.get("role") != "admin":
            raise ValueError("Superuser must have role='admin'")
        
        return self.create_user(email=email, password=password, **extra_fields)
    

class User(AbstractBaseUser, PermissionsMixin):
    
    ROLE = (
        ("customer", "Customer"),
        ("brand", "Brand"),
        ("admin", "Admin")
    )
    
    email = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=18)
    date_of_birth = models.DateField(blank=True, null=True)
    role = models.CharField(choices=ROLE, max_length=20, default="customer")
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    mail_verified = models.BooleanField(default=False)
    subscription_status= models.BooleanField(default=False)
    brand_request_id = models.CharField(max_length=256, blank=True, null=True)
    last_logout = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateField(auto_now_add=True)  # Renamed for clarity (was 'joins')
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    def __str__(self):
        return str(self.email)
    
    
class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mail_verification')
    token = models.CharField(max_length=100, unique=True, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        token_display = self.token[:5] + "..." if self.token else "no token"
        
        return f"{self.user.email}'s token : {token_display}"
    
    def is_valid(self):
        return timezone.now() <= self.expires_at
    

    

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Reset code for {self.user.email} - Code: {self.code}"
    
    def is_valid(self):
        return timezone.now() <= self.expires_at and not self.used
    
    

class BrandAccountRequest(models.Model):
    brand_name = models.CharField(max_length=100)
    brand_logo = models.ImageField(upload_to='brand_request_logo/', blank=True, null=True)
    brand_sector = models.CharField(max_length=100)
    website_link = models.URLField(max_length=200, blank=True, null=True)
    owner_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=18)
    contact_details = models.TextField()
    address_line1 = models.CharField(max_length=256, blank=True, null=True)
    address_line2 = models.CharField(max_length=256, blank=True, null=True)
    document = models.FileField(upload_to='brand_documents/', blank=True, null=True)
    approved = models.BooleanField(default=False)
    brand_request_id = models.CharField(max_length=256, blank=True, null=True, unique=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.brand_request_id:
            self.brand_request_id = secrets.token_hex(32)
        return super().save(*args, **kwargs)
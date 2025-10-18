from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import User, EmailVerification, PasswordResetCode, BrandAccountRequest


# ------------------------
# Inline for Email Verification
# ------------------------
class EmailVerificationInline(admin.StackedInline):
    model = EmailVerification
    can_delete = True
    verbose_name_plural = 'Email Verification'


# ------------------------
# User Admin
# ------------------------
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'role',
        'is_staff', 'is_active', 'mail_verified',
        'phone_no', 'last_logout', 'date_joined'
    ]

    search_fields = [
        'email', 'role', 'phone_no', 'is_active', 'mail_verified'
    ]

    list_filter = [
        'role',  # Fixed: Removed non-existent 'email', 'phone_no', 'notification_type'
        'is_active', 'is_staff', 'is_superuser',
        'date_joined', 'mail_verified'  # Fixed: 'joins' → 'date_joined'; added relevant filters
    ]

    # Fields for form (exclude sensitive like password; use actions for password reset)
    fields = [
        'email', 'phone_no', 'date_of_birth',
        'role', 'is_active', 'is_staff', 'is_superuser', 'mail_verified', 'subscription_status', 'brand_request_id', 'password'
    ]
    readonly_fields = ['date_joined']  # Prevent editing auto-added fields

    inlines = [EmailVerificationInline]

    # ✅ Admins can see everything, brands cannot see this app
    def save_model(self, request, obj, form, change):
        # Standard save; password handled via admin actions or separate form
        # If adding password field, uncomment below:
        raw_password = form.cleaned_data.get("password")
        if raw_password:
            obj.set_password(raw_password)  # ✅ Hash the password

        # Force brand users to be staff + active
        if obj.role == "brand":
            obj.is_staff = True
            obj.is_active = True

        super().save_model(request, obj, form, change)

    def has_module_permission(self, request):
        if request.user.groups.filter(name="Brand").exists():
            return False
        return super().has_module_permission(request)


# ------------------------
# Email Verification Admin
# ------------------------
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['get_user_email', 'token', 'expires_at', 'is_valid']  # Added: 'is_valid' for convenience

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

    def is_valid(self, obj):
        return obj.is_valid()  # Call the model's method
    is_valid.boolean = True
    is_valid.short_description = 'Is Valid'

    search_fields = ['user__email', 'token']

    # Consolidated permission check (DRY: use a mixin if multiple)
    def has_module_permission(self, request):
        if request.user.groups.filter(name="brand").exists():
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if request.user.groups.filter(name="brand").exists():
            return False
        return super().has_view_permission(request, obj)


# ------------------------
# Password Reset Admin
# ------------------------
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['get_user_email', 'code', 'created_at', 'used', 'expires_at', 'is_valid']  # Added: 'is_valid'

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

    def is_valid(self, obj):
        return obj.is_valid()  # Call the model's method
    is_valid.boolean = True
    is_valid.short_description = 'Is Valid'

    search_fields = ['user__email', 'code']
    list_filter = ['used', 'created_at', 'expires_at']

    # Consolidated permission check
    def has_module_permission(self, request):
        if request.user.groups.filter(name="Brand").exists():
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if request.user.groups.filter(name="Brand").exists():
            return False
        return super().has_view_permission(request, obj)


# ------------------------
# Brand Account Request Admin
# ------------------------
class BrandAccountRequestAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "owner_name", "contact_email", 'approved', "submitted_at")
    list_filter = ['submitted_at', 'brand_sector', 'approved']  # Added relevant filters
    search_fields = ['brand_name', 'owner_name', 'contact_email']

    # Consolidated permission check
    def has_module_permission(self, request):
        if request.user.groups.filter(name="Brand").exists():
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if request.user.groups.filter(name="Brand").exists():
            return False
        return super().has_view_permission(request, obj)


# ------------------------
# Register models
# ------------------------
admin.site.register(User, UserAdmin)
admin.site.register(EmailVerification, EmailVerificationAdmin)
admin.site.register(PasswordResetCode, PasswordResetCodeAdmin)
admin.site.register(BrandAccountRequest, BrandAccountRequestAdmin)
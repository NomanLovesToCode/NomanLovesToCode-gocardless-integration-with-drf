from django.contrib import admin
from .models import *


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'description']
    search_fields = ['category_name']
    
    def has_module_permission(self, request):
        """Allow access for superusers, staff, and brands."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_add_permission(self, request):
        """Allow brands to add categories."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_view_permission(self, request, obj=None):
        """Allow brands to view categories."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return hasattr(request.user, 'role')



class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['subcategory_name', 'category','description']
    search_fields = ['subcategory_name', 'category__category_name']
    list_filter = ['category']
    
    def has_module_permission(self, request):
        """Allow access for superusers, staff, and brands."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_add_permission(self, request):
        """Allow brands to add subcategories."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    
    def has_view_permission(self, request, obj=None):
        """Allow brands to view subcategories."""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return hasattr(request.user, 'role')



class OfferAdmin(admin.ModelAdmin):
    list_display = [
        'brand_name','subcategory', 
        'discount_percent','is_active', 
        'start_date', 'end_date', 'user', 'created_at'
    ]
    prepopulated_fields = {'prefix':('brand_name',) }
    search_fields = ['brand_name','product', 'description', 'user__email']
    list_filter = ['is_active', 'usage_type', 'auto_voucher_generation', 'subcategory__category', 'subcategory']
    date_hierarchy = 'created_at'
    readonly_fields = ['user','created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'subcategory', 'brand_name', 'prefix', 'product')
        }),
        ('Discount Details', {
            'fields': ('description', 'batch_size', 'discount_percent')
        }),
        ('Validity & Usage', {
            'fields': ('start_date', 'end_date', 'usage_type', 'max_uses', 'is_active')
        }),
        ('Machanism', {
            'fields': ('auto_voucher_generation', 'max_vouchers_per_user', 'voucher_cooldown_hours')
        }),
        ('External Link', {
            'fields': ('brand_url',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        """
        Add 'user' field for superusers, hide it for brands.
        """
        fieldsets = super().get_fieldsets(request, obj)
        
        if request.user.is_superuser:
            # Add user field for superusers
            fieldsets = list(fieldsets)
            basic_info = list(fieldsets[0])
            fields = list(basic_info[1]['fields'])
            if 'user' not in fields:
                fields.insert(1, 'user')  # Add after subcategory
            basic_info[1]['fields'] = tuple(fields)
            fieldsets[0] = tuple(basic_info)
            return tuple(fieldsets)
        
        return fieldsets
    
    def has_module_permission(self, request):
        """
        Allow access for:
        - Superusers
        - Staff members
        - Authenticated users with 'brand' role
        """
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check for brand role
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def get_queryset(self, request):
        """
        Filter queryset based on user role.
        brands only see their own offers.
        Superusers and staff see everything.
        """
        qs = super().get_queryset(request)
        
        # Superusers f see everything
        if request.user.is_superuser:
            return qs
        
        # brands only see their own offers
        if  request.user.is_staff or hasattr(request.user, 'role') and request.user.role == "brand":
            return qs.filter(user=request.user)
        
        # Return empty queryset for other users
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        """
        Auto-assign the current user when creating a new offer (for brands).
        Superusers can manually assign users.
        """
        if not change and not request.user.is_superuser:
            # Only auto-assign for new offers by non-superusers
            obj.user = request.user
            
        if not change and request.user.is_superuser:
            obj.user = request.user
            
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make 'user' field readonly for brands.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        
        # brands cannot change the user field
        if not request.user.is_superuser and 'user' not in readonly:
            readonly.append('user')
        
        return readonly
    
    def has_add_permission(self, request):
        """
        Allow brands and superusers to add offers.
        """
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_change_permission(self, request, obj=None):
        """
        Users can only edit their own offers (except superusers/staff).
        """
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        if obj is not None:
            # Check if user owns this offer
            return obj.user == request.user
        
        # General permission check
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_delete_permission(self, request, obj=None):
        """
        Users can only delete their own offers (except superusers/staff).
        """
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        if obj is not None:
            # Check if user owns this offer
            return obj.user == request.user
        
        # General permission check
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    def has_view_permission(self, request, obj=None):
        """
        Users can only view their own offers (except superusers/staff).
        """
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        if obj is not None:
            # Check if user owns this offer
            return obj.user == request.user
        
        # General permission check
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    
class VoucherAdmin(admin.ModelAdmin):
    list_display = ['offer', 'coupon','claimed']
    search_fields = ['coupon', 'offer__brand_name', 'offer__product']
    list_filter = ['claimed']
    readonly_fields = ['claimed_by',]
    
    fieldsets = (
        
        (
            "Basic Information", {
                'fields': ('offer',)
            }
        ),
        (
            "Voucher Information", {
                'fields': ('coupon', 'claimed')
            }
        ),
        
        (
            'Metadata', {
                'fields':('claimed_by','claimed_at',),
                "classes":('collaspe',)
            }
        )
        
    )
    
    def get_fieldsets(self, request, obj=None):
        
        fieldsets = super().get_fieldsets(request, obj)
        
        return fieldsets
    
    
    def has_module_permission(self, request):
        
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    

    
    def get_queryset(self, request):
        
        qs = super().get_queryset(request)
        
        # admin see everything
        
        if request.user.is_superuser:
            return qs
        
        #brand see only his stuffs 
        if request.user.is_staff or hasattr(request.user, 'role') and request.user.role == 'brand':
            return qs.filter(offer__user=request.user)
        
        return qs.none() # if not staff and admin see nothing
    
    
    def save_model(self, request, obj, form, change):
            
        super().save_model( request, obj, form, change)
        
        
    def has_add_permission(self, request):
        
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        if user.is_staff:
            return True
        
        
        return hasattr(request.user, 'role') and request.user.role == "brand"


    def has_change_permission(self, request, obj=None):
        
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        if user.is_staff:
            return True
        
        if obj is not None:
            return obj.offer.user == user
        
        return hasattr(request.user, 'role') and request.user.role == "brand"

    def has_delete_permission(self, request, obj=None):
        
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        if user.is_staff:
            return True
        
        if obj is not None:
            return obj.offer.user == user
        
        return hasattr(request.user, 'role') and request.user.role == "brand"


    def has_view_permission(self, request, obj=None):
        
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        if user.is_staff:
            return True
        
        if obj is not None:
            return obj.offer.user == user
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    
class VoucherReservationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'voucher', 'claimed_at']
    search_fields = ['user__email', 'voucher__coupon']
    readonly_fields = ['user', 'voucher', 'claimed_at']
    
    
    def has_module_permission(self, request):
        
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    
    def get_queryset(self, request):
        
        qs = super().get_queryset(request)
        
        # admin see everything
        
        if request.user.is_superuser:
            return qs
        
        #brand see only his stuffs 
        if request.user.is_staff or hasattr(request.user, 'role') and request.user.role == 'brand':
            return qs.filter(voucher__offer__user=request.user)
        
        return qs.none() # if not staff and admin see nothing
    
    
    def has_view_permission(self, request, obj=None):
        
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        if user.is_staff:
            return True
        
        if obj is not None:
            return obj.offer.user == user
        
        return hasattr(request.user, 'role') and request.user.role == "brand"
    
    
    


admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Voucher, VoucherAdmin)
admin.site.register(VoucherReservationLog, VoucherReservationLogAdmin)
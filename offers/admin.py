# admin.py
from django.contrib import admin
from .models import Category, SubCategory, Offer


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
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


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'category__name']
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


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = [
        'brand_name','subcategory', 
        'discount_percent', 'discount_amount', 'is_active', 
        'start_date', 'end_date', 'user'
    ]
    prepopulated_fields = {'slug': ('brand_name',)}
    search_fields = ['brand_name', 'description']
    list_filter = ['is_active', 'usage_type', 'subcategory__category', 'subcategory']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('subcategory', 'brand_name', 'slug')
        }),
        ('Discount Details', {
            'fields': ('description', 'discount_percent', 'discount_amount', 'minimum_purchase')
        }),
        ('Validity & Usage', {
            'fields': ('start_date', 'end_date', 'usage_type', 'max_uses', 'is_active')
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
        
        # Superusers and staff see everything
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
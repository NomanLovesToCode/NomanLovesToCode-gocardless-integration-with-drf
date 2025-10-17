from django.db import models
from accounts.models import User

# Create your models here.


class UserProfile(models.Model):
    STATUS = [
        ('employed', 'Employed'),
        ('retired', 'Retired'),
        ('volunteer', 'Volunteer')
    ]
    
    
    JOB = [
        ('ambulance_service','Ambulance Service'),
        ('apha','APHA'),
        ('blood_bike','Blood Bike'),
        ('dental_practice','Dental Practice')
    ]
    
    
    EMPLOYER = [
        ('ambulance_service','Ambulance Service'),
        ('fire_service','Fire Service'),
        ('hm_coustguard','HM Coastguard'),
        ('independent_lifeboat','Independent Lifeboat'),
        ('nhs','NHS'),
        ('police','Police'),
        ('red_cross','Red Cross'),
        ('rnli','RNLI'),
        ('search_and_rescue','Search and Rescue')
    ]
    
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    first_name = models.CharField(
        max_length=100,
        default="Test"
    )
    
    last_name = models.CharField(
        max_length=100,
        default="User"
    )
    
    profile_picture = models.ImageField(
        upload_to='user_profile_picture/',
        blank=True, null=True
    )
    
    employment_status = models.CharField(
        max_length=100,
        choices=STATUS,
        default='employed'
    )
    
    job_details = models.TextField(max_length=100, choices=JOB, default='ambulance')
    employer = models.CharField(max_length=100, choices=EMPLOYER, default='ambulance')
    id_card_front = models.FileField(upload_to='id_cards/', null=True, blank=True)
    id_card_back = models.FileField(upload_to='id_cards/', null=True, blank=True)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    subscription_status = models.BooleanField(default=False)
    mandate_id = models.CharField(max_length=1024, blank=True, null=True) # Gocardless Mandate ID
    customer_id = models.CharField(max_length=1024, blank=True, null=True) # Gocardless Customer ID
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    
    
    
class BrandProfile(models.Model):
    brand = models.OneToOneField(User, on_delete=models.CASCADE, related_name='brand_profile')
    brand_name = models.CharField(max_length=256)
    brand_logo = models.ImageField(upload_to='brand_logo/', blank=True, null=True)
    brand_website = models.URLField(blank=True, null=True)
    brand_sector = models.CharField(max_length=256, blank=True, null=True)
    brand_owner = models.CharField(max_length=256, blank=True, null=True)
    brand_document = models.FileField(upload_to='brand_docs/', blank=True, null=True)
    brand_address_line1 = models.CharField(max_length=256, blank=True, null=True)
    brand_address_line2 = models.CharField(max_length=256, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.brand_name} has partnered with since {self.created_at}'
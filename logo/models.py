from django.db import models

# Create your models here.

class CompanyLogo(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to="logos/")
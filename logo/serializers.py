from .models import CompanyLogo

from rest_framework import serializers

class CompanyLogoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CompanyLogo
        fields = ['id','name','logo']
        read_only_fields = ['id']
        
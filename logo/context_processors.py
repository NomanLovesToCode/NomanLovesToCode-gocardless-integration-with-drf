from .models import CompanyLogo

def site_settings(request):
    return {"site_settings": CompanyLogo.objects.first()}
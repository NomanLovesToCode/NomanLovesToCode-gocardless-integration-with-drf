
from django.urls import path
from .views import *


urlpatterns=[
    path('logo/', CompanyLogoView.as_view())   
]
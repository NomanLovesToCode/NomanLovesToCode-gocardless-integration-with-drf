from django.urls import path
from .views import *

urlpatterns=[
    path('', UserProfileView.as_view()),
    path('update-profile/',BasicProfileUpdateView.as_view())
]
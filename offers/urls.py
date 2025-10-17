# urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('category/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('offers/<int:pk>/', OfferDetailView.as_view(), name='offer-detail'),
    path('voucher/<int:pk>/', VoucherDetailView.as_view(), name='coupon-code') # pk of the related offer of this voucher
]
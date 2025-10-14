# urls.py
from django.urls import path
from .views import CategoryListView, CategoryDetailView, OfferDetailView


urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    path('offers/<slug:slug>/', OfferDetailView.as_view(), name='offer-detail'),
]
from django.urls import path
from .views import SubscribeView, UnsubscribeView, CreateCampaignView

app_name = 'notifications'

urlpatterns = [
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('unsubscribe/', UnsubscribeView.as_view(), name='unsubscribe'),
    path('campaigns/create/', CreateCampaignView.as_view(), name='create_campaign'),
]
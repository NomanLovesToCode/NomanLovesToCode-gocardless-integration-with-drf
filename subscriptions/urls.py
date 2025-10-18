# subscriptions/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('create-mandate/', CreateBillingRequest.as_view()),
    path('complete-mandate/', CompleteMandate.as_view()),  # NEW: POST for token completion
    path('cancel-mandate/', CancelMandate.as_view()),
    path('mandate-status/', MandateStatus.as_view()),  # Polling endpoint
    path('cancel-subscription/', CancelSubscription.as_view()),
    path('gocardless-complete/', RedirectComplete.as_view()),
    path('webhook/', WebhookHandler.as_view())
]
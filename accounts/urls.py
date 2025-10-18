from django.urls import path
from .views import *


urlpatterns = [
    path('register/', UserRegistrationView.as_view()),
    path('mail-verification/<str:token>/', EmailVerificationView.as_view(), name ='mail-verification'),
    path('brand-account-request/', BrandAccountRequestView.as_view()),
    path('resend-verification/', ResendMailVerificationView.as_view()),
    path('login/', UserLoginView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('forget-password/', ForgetPasswordRequestView.as_view()),
    path('otp-validation/', CheckResetCodeView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),
    path('logout/', UserLogoutView.as_view()),
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),  
]

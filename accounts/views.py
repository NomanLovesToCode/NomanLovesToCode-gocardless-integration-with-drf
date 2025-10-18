from django.contrib.auth.models import update_last_login
from django.utils import timezone
from django.urls import reverse

from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import *
from .serializers import *
from .tasks import mail_send
from .services.google_auth import GoogleAuthService
from user_consent.consent_service import UserConsentService
from notifications.marketing_service import MarketingPreferenceService

import secrets
import random
import logging
logger = logging.getLogger(__name__)
# Create your views here.


class UserRegistrationView(CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=RegistrationSerializer,
        responses={
            200: OpenApiResponse(description="Verification mail has been sent"),
            400: OpenApiResponse(description="Bad request (e.g., email sending failed)"),
        },
        description="Register a new user and send a verification email with token.",
        summary="User Registration",
    )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        mail_obj = EmailVerification.objects.get(user=user) # Not creating EmailVerification object but getting it because I have created this object at the time of user creation via signals
        
        token = mail_obj.token
        
        # Building URL dynamically using request
        verification_path = reverse('mail-verification', kwargs={'token': token})
        # Get the full URL with domain
        url = request.build_absolute_uri(verification_path)
        
        logger.info(f'Generated URL using that token is: {url}')
        
        try:
            subject = "Verify your mail"
            message = f'''Click on the link or copy & paste the link on your browser to verify your mail.
                
                Url: {url}
                
                Do not share this link with others for security reasons. The link will be valid for 1 hour
                '''
        
            mail_send.delay(user.email, subject, message)
            
            logger.info("Mail sent successfully.")
            
            return Response(
                {'detail': "Verification mail has been sent. Check your mail box."},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error("Couldn't send mail", exc_info=True)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=RegistrationSerializer,
        responses={
            200: OpenApiResponse(description="Mail has been verified successfully"),
            404: OpenApiResponse(description="Invalid token passed"),
            408: OpenApiResponse(description="Token expired, please register again"),
        },
        description="Verification of email with token.",
        summary="Email Verification",
    )
    
    def get(self, request, token):
        try:
            
            verification_token = EmailVerification.objects.get(token=token)
                                    
            if verification_token.is_valid():
                user = verification_token.user
                user.is_active = True
                user.mail_verified = True
                user.role = "customer"
                user.save()

                ref_token = RefreshToken.for_user(user)
                logger.debug(f"refresh token: {str(ref_token)}")
                response = {
                    "email": user.email,
                    "first_name": user.profile.first_name,
                    "last_name": user.profile.last_name,
                    "access_token": str(ref_token.access_token),
                    "refresh_token": str(ref_token)
                }

                return Response(
                    {
                        "detail": "Mail has been verified successfully",
                        "user_data": RegistrationResponseSerializer(response).data
                    },
                    status=status.HTTP_200_OK
                )

            else:
                user = verification_token.user
                user.delete()
                return Response(
                    {"detail": "Verification Expired. Please create a new account"},
                    status=status.HTTP_408_REQUEST_TIMEOUT
                )

        except EmailVerification.DoesNotExist:
            return Response(
                {"detail": "Token Not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class ResendMailVerificationView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=ResendVerificationRequestSerializer,
        responses={
            200: OpenApiResponse(description="Verification mail has been sent"),
            400: OpenApiResponse(description="Error: Bad Request, mail already verified"),
            404: OpenApiResponse(description="Error: User not found"),
        },
        description="Resend verification email with token.",
        summary="Resend Verification Email",
    )
    
    def post(self, request):
        email = request.data.get("email")
        
        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found: {user}")
            if user.mail_verified:
                logger.info("Mail is already verified. Please login.")
                return Response(
                    {"detail": "Mail is already verified. Please login."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            else:
                mail_obj = EmailVerification.objects.get(user=user)  # getting the previous mail that created with signals at the time of user creatiion
                logger.debug(f"Mail object: {mail_obj}")
                
                import secrets
                token = secrets.token_urlsafe(32)
                mail_obj.token = token
                mail_obj.expires_at = timezone.now() + timezone.timedelta(hours=1)
                mail_obj.save()
                
                # Build URL dynamically using request
                verification_path = reverse('mail-verification', kwargs={'token': token})
                # Get the full URL with domain
                url = request.build_absolute_uri(verification_path)
                
                try:
                    subject = 'Verify your mail'
                    message = f'''Click on the link or copy & paste the link on your browser to verify your mail.
                        
                        Url: {url}
                        
                        Do not share this link with others for security reasons. The link will be valid for 1 hour
                        '''
                        
                    mail_send.delay(user.email, subject, message)
                    
                    logger.info("Mail sent successfully.")
                    return Response(
                        {'detail': "Verification mail has been sent. Check your mail box."},
                        status=status.HTTP_200_OK
                    )
                except Exception as e:
                    logger.error("Couldn't send mail", exc_info=True)
                    return Response(
                        {"detail": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except User.DoesNotExist:
            return Response(
                {"detail": "No user found."}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['accounts'],
        responses={
            200: OpenApiResponse(description="Google login URL provided"),
        },
        description="Get the Google OAuth authorization URL for login.",
        summary="Google Login",
    )

    def get(self, request):
        google_auth = GoogleAuthService()
        auth_url = google_auth.get_auth_url(request)  # Pass request for state/session if needed
        return Response({'auth_url': auth_url}, status=status.HTTP_200_OK)


class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['accounts'],
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description="Invalid code or user creation failed"),
        },
        description="Handle Google OAuth callback and issue JWT tokens.",
        summary="Google Callback",
    )

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')  # Optional: Validate state for CSRF

        if not code:
            return Response({'error': 'Authorization code not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            google_auth = GoogleAuthService()
            tokens = google_auth.exchange_code_for_tokens(code, state)  # Pass state if used
            user_info = google_auth.get_user_info(tokens['access_token'])

            # Extract user data
            email = user_info.get('email')
            first_name = user_info.get('given_name', '')
            last_name = user_info.get('family_name', '')
            picture = user_info.get('picture', '')

            if not email:
                return Response({'error': 'No email found in Google profile'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'customer',
                    'is_active': True,  # Auto-activate for social login
                    'mail_verified': True,  # Assume verified via Google
                }
            )

            if created:

                # Set minimal consents for social users (adjust as needed)
                UserConsentService.record_consent(
                    user,
                    agreed_to_terms_and_conditions=True,
                    agreed_to_policy=True,
                    agreed_to_sms_marketing=False,
                    agreed_to_email_marketing=True,
                    agreed_to_push_notifications=False
                )
                MarketingPreferenceService.record_preference(
                    user,
                    agreed_to_sms_marketing=False,
                    agreed_to_email_marketing=False,
                    agreed_to_push_notifications=False
                )
                logger.info(f"Created new user via Google: {user.email}")

            # Update last login
            update_last_login(None, user)

            # Generate tokens
            refresh_token = RefreshToken.for_user(user)
            access_token = refresh_token.access_token

            response_data = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "refresh_token": str(refresh_token),
                "access_token": str(access_token),
            }

            return Response(
                {"detail": LoginResponseSerializer(response_data).data},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Google callback error: {e}", exc_info=True)
            return Response({'error': 'Failed to authenticate with Google'}, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["accounts"],
        request=LoginSerializer,
        responses={
            202: LoginResponseSerializer,
            400: OpenApiResponse(description="Error: Bad Request"),
            500: OpenApiResponse(description="Error: Internal Server Error"),
        },
        description="Login a user and return JWT tokens.",
        summary="User Login",
    )
    
    def post(self, request):
        
        try:
            serializer = self.serializer_class(data=request.data)
            logger.info(f"Login data received: {request.data}")
            serializer.is_valid(raise_exception=True)
            
            user = serializer.validated_data["user"]
            update_last_login(None, user)
            logger.info(f"Authenticated user: {user}")
            
            # Special login logic for admin
            
            profile, created = UserProfile.objects.get_or_create(
            user=user, 
            defaults={'first_name': 'Hey', 'last_name': 'Admin'}
        )
            
            email = user.email
            first_name = user.profile.first_name
            last_name = user.profile.last_name
            
            refresh_token = RefreshToken.for_user(user)
            access_token = refresh_token.access_token
            
            response = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "refresh_token": str(refresh_token),
                "access_token": str(access_token)
            }
            
            login_response = LoginResponseSerializer(response)
            
            logger.info(f"LoginResponse: {login_response}")
            logger.info(f"LoginResponse.data: {login_response.data}")
            
            return Response(
                {"detail": login_response.data},
                status=status.HTTP_202_ACCEPTED
            )
            
        except serializers.ValidationError as e:
            logger.error("Validation error during login", exc_info=True)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error("Error during login", exc_info=True)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            
class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer
    
    @extend_schema(
        tags=["accounts"],
        request=ChangePasswordSerializer,
        responses={
            202: OpenApiResponse(description="success: OK"),
            400: OpenApiResponse(description="Error: Bad Request"),
            500: OpenApiResponse(description="Error: Internal Server Error"),
        },
        description="Login a user and return JWT tokens.",
        summary="User Login",
    )
    def patch(self, request):
        
        password = request.data['old_password']
        new_password = request.data['new_password']
        
        user =  request.user       

        if not user.check_password(raw_password=password):
            return Response({'error': 'Wrong password'}, status=400)
        else:
            user.set_password(new_password)
            user.save()
            return Response({'success': 'password changed successfully'}, status=200)




class ForgetPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=ForgetPasswordRequestSerializer,
        responses={
            200: OpenApiResponse(description="Password reset code sent"),
            400: OpenApiResponse(description="Error: Bad Request"),
            404: OpenApiResponse(description="Error: User not found"),
        },
        description="Request password reset code.",
        summary="Forget Password Request",
    )
    def post(self, request):
        serializer = ForgetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get("email")
        
        try:
            user = User.objects.get(email=email)
            
            # Fixed: Generate 4-digit code before create
            code = f"{random.randint(100000, 999999)}"
            reset_code = PasswordResetCode.objects.create(
                user=user,
                code=code,
                expires_at=timezone.now() + timezone.timedelta(minutes=10)
            )             
            subject = "Password Reset Code"
        
            message = f'''Your password reset code is: {reset_code.code}
                    
                    This code will expire in 10 minutes. Do not share this code with others for security reasons.
                    ''' 
            mail_send.delay(user.email, subject, message)
            
            return Response(
                {'detail': "Password reset code has been sent to your email."},
                status=status.HTTP_200_OK
            ) 
                
            # Next part is handled by ResetPasswordView
            
        except User.DoesNotExist:
            return Response(
                {'detail': "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )



class CheckResetCodeView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=CheckResetCodeSerializer,
        responses={
            200: OpenApiResponse(description="Reset code is valid"),
            400: OpenApiResponse(description="Error: Bad Request"),
        },
        description="Check if the reset code is valid.",
        summary="Check Reset Code",
    )
    def post(self, request):
        serializer = CheckResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # All validation is done in serializer
        # Just mark the code as used and return success
        reset_code = serializer.validated_data['reset_code']
        reset_code.used = True
        reset_code.save()
        
        return Response(
            {'detail': "Now you can change your password"},
            status=status.HTTP_200_OK
        )
        
        


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['accounts'],
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password has been reset successfully"),
            400: OpenApiResponse(description="Error: Bad Request"),
            404: OpenApiResponse(description="Error: User not found"),
        },
        description="Reset password (assumes code was validated separately).",
        summary="Reset Password",
    )
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")
        
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()   
            return Response(
                {'detail': "Password has been reset successfully."},
                status=status.HTTP_200_OK
            )              

        except User.DoesNotExist:
            return Response(
                {'detail': "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
            
            


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(  # Added: For docs
        tags=['accounts'],
        request=None,
        responses={
            200: OpenApiResponse(description="User logged out successfully"),
            400: OpenApiResponse(description="Invalid token"),
        },
        description="Logout user and blacklist token.",
        summary="User Logout",
    )
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")  # Get refresh token from request data
            
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Update user's last logout time
            user = request.user
            user.last_logout = timezone.now()
            user.save(update_fields=["last_logout"])
            
            logger.info(f"User {user.id} logged out successfully")
            
            return Response(
                {"detail": "User logged out successfully."},
                status=status.HTTP_200_OK
            )
            
        except TokenError:
            logger.warning(f"Invalid refresh token provided for user {request.user.id}")
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error during logout for user {request.user.id}", exc_info=True)
            return Response(
                {"detail": "An error occurred during logout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class BrandAccountRequestView(CreateAPIView):
    serializer_class = BrandAccountRequestSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=['accounts'],
        request=BrandAccountRequestSerializer,
        responses={
            201: OpenApiResponse(description="Brand account request submitted successfully"),
            400: OpenApiResponse(description="Bad request"),
        },
        description="Submit a Brand account request.",
        summary="Brand Account Request",
    )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Request submitted successfully"}, status=status.HTTP_201_CREATED)
            
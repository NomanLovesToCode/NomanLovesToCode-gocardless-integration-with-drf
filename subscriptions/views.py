# subscriptions/views.py
import logging
import gocardless_pro as client
import gocardless_pro
from gocardless_pro import webhooks
from gocardless_pro.errors import InvalidSignatureError
from decimal import Decimal
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.views.generic import View
from django.utils import timezone
from django.shortcuts import redirect
from datetime import timedelta, datetime
import secrets

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication

from drf_spectacular.utils import extend_schema

from accounts.models import User
from .models import Subscription
from .serializers import *
from Helyar1_Backend.clients import gocardless_client

logger = logging.getLogger(__name__)


def has_active_subscription(user):
    """Helper to check if user has a real active sub (not pending)"""
    try:
        subscription = Subscription.objects.get(user=user)
        return subscription.is_valid() and subscription.is_active and subscription.status != 'pending'
    except Subscription.DoesNotExist:
        return False


class CreateBillingRequest(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: CreateMandateResponseSerializer,
            400: ErrorResponseSerializer
        }
    )
    def post(self, request):
        user = request.user
        logger.info(f"Creating billing request for user: {user.email} (ID: {user.id})")
        
        # Make sure user has a profile
        if not hasattr(user, 'profile'):
            logger.error(f"User {user.email} has no profile")
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Don't allow if mandate already set up
        if user.profile.mandate_id:
            logger.warning(f"User {user.email} already has mandate: {user.profile.mandate_id}")
            return Response(
                {'error': 'Mandate already exists. Proceed to create subscription.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # No duplicate active subs
        if has_active_subscription(user):
            logger.warning(f"User {user.email} already has active subscription")
            return Response(
                {'message': 'You already have an existing active subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create subscription record
        subscription, created = Subscription.objects.get_or_create(user=user)
        logger.info(f"Subscription {'created' if created else 'found'} for user {user.email}")
        
        # Generate state for CSRF (stored in DB, frontend must pass back on complete)
        state = secrets.token_urlsafe(32)
        subscription.temp_state = state
        subscription.status = 'pending'
        subscription.save()
        
        # Billing params
        billing_params = {
            'payment_request': {
                'amount': int(subscription.price * 100),
                'currency': 'GBP',
                'description': '1 Year access fee',
            },
            'mandate_request': {
                'scheme': 'bacs',
                'currency': 'GBP',
                'metadata': {
                    'user_id': str(user.id),
                    'plan': 'yearly subscription'
                },
                'verify': 'recommended'
            },
            'metadata': {
                'user_id': str(user.id),
                'subscription_id': str(subscription.id)
            }
        }
        
        try:
            # Create billing request
            logger.info(f"Creating GoCardless billing request for user {user.email}")
            billing_request = gocardless_client.billing_requests.create(billing_params)
            billing_request_id = billing_request.id
            logger.info(f"Billing request created: {billing_request_id}")
            
            # FIXED: Use proper redirect_uri for GoCardless callback
            # GoCardless will append ?redirect_flow_id=XXX to this URL
            billing_flow_params = {
                'redirect_uri': 'https://lelia-leafed-lashandra.ngrok-free.dev/api/subscriptions/gocardless-complete/',
                'exit_uri': 'https://lelia-leafed-lashandra.ngrok-free.dev/?error=user_cancelled',
                'links': {
                    'billing_request': billing_request_id
                },
                'prefilled_customer': {
                    'email': user.email,
                    'given_name': user.profile.first_name,
                    'family_name': user.profile.last_name,
                }
            }
            
            logger.info(f"Creating billing flow for user {user.email}")
            billing_flow = gocardless_client.billing_request_flows.create(billing_flow_params)
            logger.info(f"Billing flow created: {billing_flow.id}")
            
            # Store in database for webhook processing
            subscription.temp_flow_id = billing_flow.id
            subscription.temp_billing_request_id = billing_request_id
            subscription.save()
            logger.info(f"Stored flow_id and billing_request_id in database for user {user.email}")
            
            return Response({
                'status': 'started',
                'billing_request_id': billing_request_id,
                'authorisation_url': billing_flow.authorisation_url,
                'state': state
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Billing request creation failed for user {user.email}: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CompleteMandate(APIView):
    """
    FIXED: This endpoint should be called programmatically after RedirectComplete
    extracts the redirect_flow_id from GoCardless callback
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=CompleteMandateSerializer,
        responses={
            200: CompleteMandateSerializer,
            400: ErrorResponseSerializer
        }
    )
    def post(self, request):
        flow_id = request.data.get('flow_id')  # FIXED: renamed from flow_token
        state = request.data.get('state')
        
        if not flow_id:
            logger.error("Missing flow_id in request")
            return Response({'error': 'Missing flow_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # FIXED: Complete the billing request flow (not billing_request_flows)
            logger.info(f"Completing billing flow: {flow_id}")
            complete_response = gocardless_client.billing_request_flows.complete(flow_id)
            
            # The response contains the billing_request in links
            billing_request_id = complete_response.links.billing_request
            
            # Now fetch the full billing request
            billing_request = gocardless_client.billing_requests.get(billing_request_id)
            logger.info(f"Billing request status: {billing_request.status}")
            
            if billing_request.status != 'fulfilled':
                return Response({
                    'error': 'Billing request not fulfilled',
                    'details': billing_request.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Extract details
            mandate_id = billing_request.links.mandate_request_mandate
            customer_id = billing_request.links.customer
            payment_id = getattr(billing_request.links, 'payment', None)
            
            # Find subscription
            try:
                subscription = Subscription.objects.get(temp_billing_request_id=billing_request_id)
                user = subscription.user
                
                # Optional CSRF validation
                if state and subscription.temp_state != state:
                    logger.warning(f"State mismatch for user {user.email}")
                    return Response({'error': 'Invalid state (CSRF mismatch)'}, status=status.HTTP_400_BAD_REQUEST)
                
            except Subscription.DoesNotExist:
                logger.error(f"No subscription found for billing_request_id: {billing_request_id}")
                return Response({'error': 'Subscription not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Update profile
            user.profile.mandate_id = mandate_id
            user.profile.customer_id = customer_id
            user.profile.save()
            logger.info(f"Updated profile for user {user.email}: mandate={mandate_id}, customer={customer_id}")
            
            # Create subscription on GoCardless
            sub_params = {
                'amount': int(subscription.price * 100),
                'currency': 'GBP',
                'interval_unit': 'yearly',
                'name': 'Helyar1 Yearly Subscription',
                'links': {'mandate': mandate_id},
                'metadata': {'user_id': str(user.id)},
            }
            
            sub_response = gocardless_client.subscriptions.create(params=sub_params)
            logger.info(f"GoCardless subscription created: {sub_response.id}")
            
            # Update local DB
            subscription.subscription_id = sub_response.id
            subscription.status = 'active'
            subscription.is_active = True
            subscription.started_at = timezone.now()
            subscription.temp_flow_id = None
            subscription.temp_billing_request_id = None
            subscription.temp_state = None
            
            # Set expiry date
            if hasattr(sub_response, 'upcoming_payments') and sub_response.upcoming_payments:
                subscription.expires_at = datetime.fromisoformat(sub_response.upcoming_payments[0]['charge_date'].replace('Z', '+00:00'))
            else:
                subscription.expires_at = timezone.now() + timedelta(days=365)
            
            subscription.save()
            
            # Sync user flags
            user.subscription_status = True
            user.save()
            user.profile.subscription_status = True
            user.profile.save()
            
            logger.info(f"SUCCESS: Subscription activated for user {user.email}")
            
            return Response({
                'status': 'completed',
                'mandate_id': mandate_id,
                'customer_id': customer_id,
                'payment_id': payment_id,
                'subscription_id': sub_response.id,
                'next_charge_date': subscription.expires_at.isoformat() if subscription.expires_at else None,
                'message': 'Direct debit setup and subscription activated successfully!'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Complete mandate failed: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelMandate(APIView):
    """FIXED: Simplified mandate cancellation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if not hasattr(user, 'profile') or not user.profile.mandate_id:
            return Response(
                {'error': 'No mandate found for this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            mandate_id = user.profile.mandate_id
            logger.info(f"Cancelling mandate {mandate_id} for user {user.email}")
            
            # Cancel the mandate
            mandate = gocardless_client.mandates.cancel(mandate_id)
            
            # Clear from profile
            user.profile.mandate_id = None
            user.profile.customer_id = None
            user.profile.save()
            
            logger.info(f"Mandate cancelled successfully for user {user.email}")
            
            return Response({
                'status': mandate.status,
                'message': 'Mandate cancelled successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to cancel mandate for user {user.email}: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class MandateStatus(APIView):
    """
    Status check endpoint - called after GoCardless redirect for polling.
    Frontend should poll this endpoint to check if subscription is ready.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: MandateStatusResponseSerializer,
            400: ErrorResponseSerializer
        }
    )
    def get(self, request):
        user = request.user
        
        try:
            subscription = Subscription.objects.get(user=user)
            
            # Check if completed
            if subscription.status == 'active' and subscription.is_active and subscription.subscription_id:
                logger.info(f"Subscription active for user {user.email}")
                return Response({
                    'status': 'completed',
                    'subscription_id': subscription.subscription_id,
                    'mandate_id': user.profile.mandate_id if hasattr(user, 'profile') else None,
                    'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
                    'message': 'Subscription is active!'
                }, status=status.HTTP_200_OK)
            
            # Check if still pending but not timed out
            elif subscription.status == 'pending':
                age = timezone.now() - subscription.created_at
                if age > timedelta(minutes=10):
                    logger.warning(f"Subscription setup timed out for user {user.email}")
                    return Response({
                        'status': 'timeout',
                        'message': 'Setup timed out. Please try again.'
                    }, status=status.HTTP_408_REQUEST_TIMEOUT)
                else:
                    logger.info(f"Subscription still processing for user {user.email}")
                    return Response({
                        'status': 'processing',
                        'message': 'Setting up your subscription... Please wait.'
                    }, status=status.HTTP_200_OK)
            
            # Something went wrong
            else:
                logger.warning(f"Subscription in unexpected state for user {user.email}: {subscription.status}")
                return Response({
                    'status': subscription.status,
                    'message': f'Subscription status: {subscription.status}'
                }, status=status.HTTP_200_OK)
                
        except Subscription.DoesNotExist:
            logger.info(f"No subscription found for user {user.email}")
            return Response({
                'status': 'not_found',
                'message': 'No subscription found. Please start the subscription process.'
            }, status=status.HTTP_404_NOT_FOUND)


class CancelSubscription(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: CancelSubscriptionSerializer,
            400: ErrorResponseSerializer
        }
    )
    def post(self, request):
        user = request.user
        logger.info(f"Cancel subscription requested by user: {user.email}")
        
        try:
            subscription = Subscription.objects.get(user=user)
            
            if not subscription.is_active:
                logger.warning(f"User {user.email} has no active subscription")
                return Response(
                    {'error': "You don't have any active subscription"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                logger.info(f"Cancelling GoCardless subscription {subscription.subscription_id}")
                # Cancel at end of period
                cancel_params = {
                    'metadata': {'cancelled_by': str(user.id)}
                }
                gocardless_client.subscriptions.cancel(
                    subscription.subscription_id,
                    params=cancel_params
                )
                
                # Update local
                subscription.is_active = False
                subscription.status = 'cancelled'
                subscription.save()
                
                # Sync flags
                user.subscription_status = False
                user.save()
                user.profile.subscription_status = False
                user.profile.save()
                
                logger.info(f"Cancelled subscription for user {user.email}")
                
                return Response({
                    'status': 'cancelled',
                    'details': 'Subscription cancelled successfully. It will remain active until the end of the current period.'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"GoCardless cancellation failed: {str(e)}", exc_info=True)
                return Response(
                    {'error': 'Failed to cancel subscription', 'details': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Subscription.DoesNotExist:
            logger.error(f"No subscription found for user {user.email}")
            return Response(
                {'error': "You don't have any subscription"},
                status=status.HTTP_404_NOT_FOUND
            )


class WebhookHandler(View):
    """FIXED: Improved webhook handling"""
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        try:
            # FIXED: Get signature from correct header
            signature = request.headers.get('Webhook-Signature')
            if not signature:
                # Fallback to META
                signature = request.META.get('HTTP_WEBHOOK_SIGNATURE')
            
            body = request.body.decode('utf-8')
            
            # Verify signature - GoCardless webhooks.parse() expects positional args
            events = webhooks.parse(
                body,  # request body as string
                settings.GC_WEBHOOK_SECRET,  # webhook secret
                signature  # signature header
            )
            
            # Track processed events to avoid duplicates
            if not hasattr(self, 'processed_events'):
                self.processed_events = set()
            
            for event in events:
                if event.id in self.processed_events:
                    logger.info(f"Event {event.id} already processed, skipping")
                    continue
                
                logger.info(f"Processing webhook event: {event.id}, type: {event.resource_type}, action: {event.action}")
                self.processed_events.add(event.id)
                
                # Handle billing_request fulfilled
                if event.resource_type == 'billing_requests' and event.action == 'fulfilled':
                    self._handle_billing_fulfilled(event)
                
                # Handle payment events
                elif event.resource_type == 'payments':
                    self._handle_payment(event)
                
                # Handle mandate events
                elif event.resource_type == 'mandates':
                    self._handle_mandate(event)
                
                # Handle subscription events
                elif event.resource_type == 'subscriptions':
                    self._handle_subscription(event)
            
            return HttpResponse(status=200)
            
        except InvalidSignatureError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return HttpResponse(status=498)
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            return HttpResponse(status=200)  # Return 200 to prevent retries
    
    def _handle_billing_fulfilled(self, event):
        """Handle billing request fulfilled events"""
        try:
            billing_request_id = event.links.billing_request
            logger.info(f"Billing request fulfilled: {billing_request_id}")
            
            subscription = Subscription.objects.get(temp_billing_request_id=billing_request_id)
            user = subscription.user
            
            # Fetch billing request details
            billing_request = gocardless_client.billing_requests.get(billing_request_id)
            
            if billing_request.status == 'fulfilled':
                mandate_id = billing_request.links.mandate_request_mandate
                customer_id = billing_request.links.customer
                
                # Update profile
                user.profile.mandate_id = mandate_id
                user.profile.customer_id = customer_id
                user.profile.save()
                logger.info(f"Updated profile with mandate: {mandate_id}, customer: {customer_id}")
                
                # Create GoCardless subscription
                sub_params = {
                    'amount': int(subscription.price * 100),
                    'currency': 'GBP',
                    'interval_unit': 'yearly',
                    'name': 'Helyar1 Yearly Subscription',
                    'links': {'mandate': mandate_id},
                    'metadata': {'user_id': str(user.id)},
                }
                
                sub_response = gocardless_client.subscriptions.create(params=sub_params)
                logger.info(f"Created GoCardless subscription: {sub_response.id}")
                
                # Update local subscription
                subscription.subscription_id = sub_response.id
                subscription.status = 'active'
                subscription.is_active = True
                subscription.started_at = timezone.now()
                
                # Set expiry date
                if hasattr(sub_response, 'upcoming_payments') and sub_response.upcoming_payments:
                    from datetime import datetime
                    subscription.expires_at = datetime.fromisoformat(
                        sub_response.upcoming_payments[0]['charge_date'].replace('Z', '+00:00')
                    )
                else:
                    subscription.expires_at = timezone.now() + timedelta(days=365)
                
                # Clear temp fields
                subscription.temp_billing_request_id = None
                subscription.temp_flow_id = None
                subscription.temp_state = None
                subscription.save()
                
                # Sync user flags
                user.subscription_status = True
                user.save()
                user.profile.subscription_status = True
                user.profile.save()
                
                logger.info(f"SUCCESS: Webhook set mandate: {mandate_id}, customer: {customer_id}, subscription: {sub_response.id} for user {user.email}")
            else:
                logger.warning(f"Billing request {billing_request_id} not fulfilled: {billing_request.status}")
        
        except Subscription.DoesNotExist:
            logger.error(f"No subscription found for billing_request_id: {event.links.billing_request}")
        except Exception as e:
            logger.error(f"Error processing billing fulfilled: {str(e)}", exc_info=True)
    
    def _handle_payment(self, event):
        """Handle payment events"""
        try:
            sub_id = getattr(event.links, 'subscription', None)
            if not sub_id:
                return
            
            subscription = Subscription.objects.get(subscription_id=sub_id)
            user = subscription.user
            
            if event.action == 'confirmed' or event.action == 'paid_out':
                subscription.status = 'active'
                subscription.is_active = True
                
                # Fetch subscription to get next charge date
                gc_sub = gocardless_client.subscriptions.get(sub_id)
                if hasattr(gc_sub, 'upcoming_payments') and gc_sub.upcoming_payments:
                    subscription.expires_at = datetime.fromisoformat(
                        gc_sub.upcoming_payments[0]['charge_date'].replace('Z', '+00:00')
                    )
                else:
                    subscription.expires_at = timezone.now() + timedelta(days=365)
                
                subscription.save()
                
                # Sync user flags
                user.subscription_status = True
                user.save()
                user.profile.subscription_status = True
                user.profile.save()
                
                logger.info(f"Payment confirmed - activated subscription for {user.email}")
                
            elif event.action == 'failed':
                subscription.is_active = False
                subscription.status = 'inactive'
                subscription.save()
                
                user.subscription_status = False
                user.save()
                user.profile.subscription_status = False
                user.profile.save()
                
                logger.warning(f"Payment failed - deactivated subscription for {user.email}")
                
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for sub_id: {sub_id}")
        except Exception as e:
            logger.error(f"Error handling payment: {str(e)}", exc_info=True)
    
    def _handle_mandate(self, event):
        """Handle mandate events"""
        if event.action in ['cancelled', 'failed', 'expired']:
            try:
                mandate_id = event.links.mandate
                # Find user by mandate_id
                profile = User.objects.get(profile__mandate_id=mandate_id).profile
                logger.warning(f"Mandate {mandate_id} {event.action} for user {profile.user.email}")
            except User.DoesNotExist:
                logger.error(f"No user found for mandate: {mandate_id}")
    
    def _handle_subscription(self, event):
        """Handle subscription events"""
        try:
            sub_id = event.links.subscription
            subscription = Subscription.objects.get(subscription_id=sub_id)
            
            if event.action == 'cancelled':
                subscription.is_active = False
                subscription.status = 'cancelled'
                subscription.save()
                logger.info(f"Subscription {sub_id} cancelled via webhook")
                
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found: {sub_id}")


class RedirectComplete(APIView):
    """
    FIXED: GoCardless callback handler for Billing Request Flow
    The Billing Request Flow doesn't send redirect_flow_id in the callback.
    Instead, we rely on webhooks to complete the setup.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        full_url = request.build_absolute_uri()
        logger.info(f"RedirectComplete hit: {full_url}")
        logger.info(f"GET params: {dict(request.GET)}")
        
        # For Billing Request Flow, GoCardless doesn't send parameters
        # The flow is completed via webhooks instead
        # We just redirect user back to frontend with a "processing" status
        
        # Check if there's a redirect_flow_id (old Redirect Flow API - unlikely)
        redirect_flow_id = request.GET.get('redirect_flow_id')
        
        if redirect_flow_id:
            # Old Redirect Flow API (keep for backward compatibility)
            logger.info(f"Using old Redirect Flow API with id: {redirect_flow_id}")
            return self._handle_old_redirect_flow(redirect_flow_id)
        
        # New Billing Request Flow - just redirect with processing status
        # The webhook will handle the actual completion
        logger.info("Billing Request Flow detected - redirecting to frontend")
        return redirect(f'{settings.BASE_FRONTEND_URL}/?status=processing&message=setting_up_subscription')
    
    def _handle_old_redirect_flow(self, redirect_flow_id):
        """Handle old Redirect Flow API (for backward compatibility)"""
        try:
            logger.info(f"Completing redirect flow: {redirect_flow_id}")
            complete_response = gocardless_client.redirect_flows.complete(
                redirect_flow_id,
                params={'session_token': 'dummy_session_token'}
            )
            
            mandate_id = complete_response.links.mandate
            customer_id = complete_response.links.customer
            
            # Find user by checking recent pending subscriptions
            # This is a fallback - normally webhooks handle this
            logger.info(f"Mandate created: {mandate_id}, Customer: {customer_id}")
            
            return redirect(f'{settings.BASE_FRONTEND_URL}/?success=subscription_active')
            
        except Exception as e:
            logger.error(f"RedirectComplete failed: {str(e)}", exc_info=True)
            return redirect(f'{settings.BASE_FRONTEND_URL}/?error={str(e)}')


class RootHandler(APIView):
    """Simple root endpoint for success/error display"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        success = request.GET.get('success')
        error = request.GET.get('error')
        
        if success:
            msg = success.replace('_', ' ').title()
            return HttpResponse(f"""
                <html>
                    <head><title>Success - Helyar1</title></head>
                    <body style="font-family: Arial; text-align: center; padding: 50px; background: #e8f5e8;">
                        <h1 style="color: green;">✅ {msg}</h1>
                        <p>Your subscription is active! <a href="/admin/">Admin</a> | <a href="/api/accounts/login/">Login</a></p>
                    </body>
                </html>
            """, content_type='text/html')
        
        if error:
            msg = error.replace('_', ' ').title()
            return HttpResponse(f"""
                <html>
                    <head><title>Error - Helyar1</title></head>
                    <body style="font-family: Arial; text-align: center; padding: 50px; background: #ffe6e6; color: red;">
                        <h1>❌ {msg}</h1>
                        <p>Setup issue—<a href="/api/subscriptions/create-mandate/">Try Again</a> | <a href="/admin/">Admin</a></p>
                    </body>
                </html>
            """, content_type='text/html')
        
        # Default root
        return HttpResponse("""
            <html>
                <head><title>Helyar1</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Helyar1 API Ready!</h1>
                    <p><a href="/admin/">Admin</a> | <a href="/api/accounts/login/">Login</a> | <a href="/api/docs/swagger/">API Docs</a></p>
                </body>
            </html>
        """, content_type='text/html')
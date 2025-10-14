# subscriptions/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Subscription
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_expired_subscriptions():
    """
    Check for expired subscriptions and mark them accordingly.
    Run daily via Celery Beat.
    """
    logger.info("Starting expired subscriptions check")
    
    # Find subscriptions that should be expired
    expired_subs = Subscription.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now()
    )
    
    count = 0
    for sub in expired_subs:
        sub.mark_expired()
        count += 1
        logger.info(f"Expired subscription for user {sub.user.email}")
    
    logger.info(f"Completed expired subscriptions check: {count} subscriptions expired")
    return f"Expired {count} subscriptions"


@shared_task
def send_expiry_reminders():
    """
    Send reminders to users whose subscriptions are expiring soon.
    Run daily via Celery Beat.
    """
    logger.info("Starting expiry reminder task")
    
    # Find subscriptions expiring in 7 days
    reminder_date = timezone.now() + timedelta(days=7)
    expiring_soon = Subscription.objects.filter(
        is_active=True,
        status='active',
        expires_at__date=reminder_date.date()
    )
    
    count = 0
    for sub in expiring_soon:
        try:
            send_expiry_notification(sub.user, sub.expires_at)
            count += 1
            logger.info(f"Sent expiry reminder to {sub.user.email}")
        except Exception as e:
            logger.error(f"Failed to send reminder to {sub.user.email}: {str(e)}")
    
    logger.info(f"Completed expiry reminders: {count} reminders sent")
    return f"Sent {count} expiry reminders"


@shared_task
def sync_subscription_status(subscription_id):
    """
    Sync subscription status with GoCardless.
    Can be called manually or scheduled.
    """
    from Helyar1_Backend.clients import gocardless_client
    
    try:
        subscription = Subscription.objects.get(id=subscription_id)
        
        if not subscription.subscription_id:
            logger.warning(f"No GoCardless subscription_id for {subscription.user.email}")
            return "No subscription_id"
        
        # Fetch from GoCardless
        gc_sub = gocardless_client.subscriptions.get(subscription.subscription_id)
        
        logger.info(f"Syncing subscription {subscription.subscription_id}: GC status = {gc_sub.status}")
        
        # Update based on GoCardless status
        if gc_sub.status == 'active':
            subscription.is_active = True
            subscription.status = 'active'
            
            # Update expiry from upcoming payments
            if hasattr(gc_sub, 'upcoming_payments') and gc_sub.upcoming_payments:
                from datetime import datetime
                subscription.expires_at = datetime.fromisoformat(
                    gc_sub.upcoming_payments[0]['charge_date'].replace('Z', '+00:00')
                )
        
        elif gc_sub.status == 'cancelled':
            subscription.is_active = False
            subscription.status = 'cancelled'
        
        elif gc_sub.status == 'finished':
            subscription.is_active = False
            subscription.status = 'expired'
        
        subscription.save()
        
        # Sync user flags
        subscription.user.subscription_status = subscription.is_active
        subscription.user.save()
        if hasattr(subscription.user, 'profile'):
            subscription.user.profile.subscription_status = subscription.is_active
            subscription.user.profile.save()
        
        logger.info(f"Successfully synced subscription for {subscription.user.email}")
        return f"Synced subscription for {subscription.user.email}"
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription {subscription_id} not found")
        return "Subscription not found"
    except Exception as e:
        logger.error(f"Failed to sync subscription {subscription_id}: {str(e)}", exc_info=True)
        return f"Sync failed: {str(e)}"


@shared_task
def retry_failed_payment(subscription_id):
    """
    Retry a failed payment for a subscription.
    This is a placeholder - actual implementation depends on your business logic.
    """
    from Helyar1_Backend.clients import gocardless_client
    
    try:
        subscription = Subscription.objects.get(id=subscription_id)
        
        if subscription.failed_payment_count >= 3:
            logger.warning(f"Max retry attempts reached for {subscription.user.email}")
            return "Max retries reached"
        
        # Create a one-off payment
        payment_params = {
            'amount': int(subscription.price * 100),
            'currency': 'GBP',
            'description': 'Retry payment for Helyar1 subscription',
            'links': {
                'mandate': subscription.user.profile.mandate_id
            },
            'metadata': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'retry_attempt': str(subscription.failed_payment_count + 1)
            }
        }
        
        payment = gocardless_client.payments.create(params=payment_params)
        
        logger.info(f"Created retry payment {payment.id} for {subscription.user.email}")
        return f"Created retry payment: {payment.id}"
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription {subscription_id} not found")
        return "Subscription not found"
    except Exception as e:
        logger.error(f"Failed to retry payment: {str(e)}", exc_info=True)
        return f"Retry failed: {str(e)}"


def send_expiry_notification(user, expiry_date):
    """
    Send expiry notification to user.
    Integrate with your notification system (email, SMS, etc.)
    """
    # Example using Django's email system
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = "Your Helyar1 Subscription is Expiring Soon"
    message = f"""
    Hi {user.profile.first_name if hasattr(user, 'profile') else user.email},
    
    Your Helyar1 subscription is set to expire on {expiry_date.strftime('%B %d, %Y')}.
    
    Your subscription will be automatically renewed unless you cancel it.
    
    If you have any questions, please contact our support team.
    
    Best regards,
    The Helyar1 Team
    """
    
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )
    
    logger.info(f"Sent expiry notification email to {user.email}")


@shared_task
def cleanup_pending_subscriptions():
    """
    Clean up subscriptions stuck in pending state for more than 24 hours.
    Run daily via Celery Beat.
    """
    logger.info("Starting cleanup of pending subscriptions")
    
    cutoff_time = timezone.now() - timedelta(hours=24)
    stale_subs = Subscription.objects.filter(
        status='pending',
        created_at__lt=cutoff_time
    )
    
    count = 0
    for sub in stale_subs:
        # Clear temp fields
        sub.clear_temp_fields()
        sub.status = 'inactive'
        sub.save()
        count += 1
        logger.info(f"Cleaned up stale pending subscription for {sub.user.email}")
    
    logger.info(f"Completed cleanup: {count} pending subscriptions cleaned")
    return f"Cleaned {count} stale subscriptions"
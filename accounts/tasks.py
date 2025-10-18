from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from celery import shared_task

from rest_framework import serializers

import logging
logger = logging.getLogger(__name__)

import requests


@shared_task
def verify_phone_number(phone_number):
    api_key = settings.PHONE_NUMBER_VALIDATION_API_KEY
        
    url = f"https://phonevalidation.abstractapi.com/v1/?api_key={api_key}&phone={phone_number}&country_code=GB"
    try:
        response = requests.get(url)
        result = response.json()
    except Exception as e:
        logger.error(f"Error during phone number validation: {e}", exc_info=True)
        return {'valid': False, 'error': 'Error validating phone number. Please try again later.'}
    
    logger.debug(f"Phone validation response: {result}")
    
    if not result['valid']:
        return {'valid': False, 'error': 'Invalid phone number'}
    
    return {'valid': True, 'formatted': result.get('format', {}).get('international', phone_number)}


@shared_task    
def mail_send(user_email: str, subject: str, message: str, code=None):
    """
    Send email to user. Pass user_email instead of user object for Celery serialization.
    
    Args:
        user_email: Email address of the recipient
        subject: Email subject
        message: Email message body
        code: Optional verification/reset code to include
    """
    try:
        # Include code in message if provided (for reset emails)
        full_message = message if code is None else f"{message}\n\nYour code: {code}"
        
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user_email],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {user_email}: {e}", exc_info=True)
        return False
import json
import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from accounts.models import User  # Corrected import
from .models import MarketingCampaign, NotificationLog
from twilio.rest import Client  # installed


@shared_task
def send_marketing_campaign(campaign_id):
    """
    Celery task to send a marketing campaign to all eligible users.
    Filters by subscribed=True and matching notification_type.
    Updates campaign status and logs notifications.
    """
    try:
        campaign = MarketingCampaign.objects.get(id=campaign_id)
        if campaign.status != 'scheduled':
            return

        campaign.status = 'sending'
        campaign.save(update_fields=['status'])

        users = User.objects.filter(
            subscribed=True,
            notification_type=campaign.notification_type
        )  # Removed select_related for simplicity; add if needed

        for user in users:
            try:
                if campaign.notification_type == 'email':
                    send_email.delay(campaign.id, user.id)
                elif campaign.notification_type == 'sms':
                    send_sms.delay(campaign.id, user.id)
                elif campaign.notification_type == 'push':
                    # TODO: Implement push notification (e.g., via Firebase or Web Push)
                    NotificationLog.objects.create(
                        user=user, campaign=campaign, status='sent'
                    )
                    continue

                NotificationLog.objects.create(
                    user=user, campaign=campaign, status='sent'
                )
            except Exception as e:
                NotificationLog.objects.create(
                    user=user, campaign=campaign, status='failed', error=str(e)
                )

        campaign.status = 'sent'
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status', 'sent_at'])

    except MarketingCampaign.DoesNotExist:
        pass  # Campaign deleted, skip


@shared_task
def send_email(campaign_id, user_id):
    """
    Celery task to send email via Netcore Email API.
    """
    campaign = MarketingCampaign.objects.get(id=campaign_id)
    user = User.objects.get(id=user_id)

    url = "https://emailapi.netcorecloud.net/v5/mail/send"
    headers = {
        "api_key": settings.NETCORE_EMAIL_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "from": {
            "email": settings.FROM_EMAIL,
            "name": "Maximum Savings"
        },
        "subject": campaign.title,
        "content": [
            {
                "type": "html",
                "value": campaign.content
            }
        ],
        "personalizations": [
            {
                "to": [
                    {
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}".strip() or "Subscriber"
                    }
                ]
            }
        ],
        "tags": ["marketing_campaign"]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in (200, 202):
        raise Exception(f"Netcore email send failed: {response.status_code} - {response.text}")


@shared_task
def send_sms(campaign_id, user_id):
    """
    Celery task to send SMS via Twilio.
    """
    campaign = MarketingCampaign.objects.get(id=campaign_id)
    user = User.objects.get(id=user_id)

    if not user.phone_no:
        raise Exception("No phone number for user")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message_body = campaign.content[:160]  # SMS character limit

    message = client.messages.create(
        body=message_body,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=user.phone_no
    )

    if message.error_code:
        raise Exception(f"Twilio SMS failed: {message.error_message}")


@shared_task
def add_to_netcore(email, first_name='', phone_no=''):
    """
    Celery task to add subscriber to Netcore via Add Contact API.
    """
    url = "https://api.netcoresmartech.com/apiv2"  # Adjust for your IDC (US/IN/EU)
    params = {
        'type': 'contact',
        'activity': 'addsync',
        'apikey': settings.NETCORE_CE_API_KEY,
    }
    data_dict = {
        'FIRST_NAME': first_name,
        'EMAIL': email,
    }
    if phone_no:
        data_dict['MOBILE'] = phone_no

    params['data'] = json.dumps(data_dict)

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Netcore add contact failed: {response.status_code} - {response.text}")


@shared_task
def blacklist_netcore(email):
    """
    Celery task to unsubscribe/blacklist email in Netcore via Blacklist API.
    """
    url = "https://api.netcoresmartech.com/v3/contact/blacklist"  # Adjustment for my IDC
    headers = {
        'api-key': settings.NETCORE_CE_API_KEY,
        'primarykey': 'email',
        'channel': 'email',
        'Content-Type': 'application/json'
    }
    payload = {"data": [email]}

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Netcore blacklist failed: {response.status_code} - {response.text}")
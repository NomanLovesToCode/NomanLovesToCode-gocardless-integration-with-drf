from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from .serializers import SubscribeSerializer, UnsubscribeSerializer, MarketingCampaignSerializer
from .tasks import (
    add_to_netcore, blacklist_netcore, send_marketing_campaign
)
from accounts.models import User  # Corrected import


class SubscribeView(APIView):
    """
    API to handle subscription via website form.
    Creates or updates user, sets subscribed=True, defaults notification_type to 'email',
    and adds to Netcore subscriber list.
    """
    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            defaults = {
                'first_name': serializer.validated_data.get('first_name', ''),
                'last_name': serializer.validated_data.get('last_name', ''),
                'phone_no': serializer.validated_data.get('phone_no', ''),
                'role': 'customer',
                'subscribed': True,
                'notification_type': 'email',  # Default for new subscribers
                'is_active': False,  # For marketing only, unless they register fully
            }
            user, created = User.objects.get_or_create(
                email=email,
                defaults=defaults
            )
            if not created:
                user.subscribed = True
                user.notification_type = defaults['notification_type']  # Ensure preference
                user.save(update_fields=['subscribed', 'notification_type'])

            # Async add to Netcore
            add_to_netcore.delay(
                email,
                user.first_name,
                user.phone_no or ''
            )

            return Response({
                'message': 'Subscribed successfully for marketing notifications.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnsubscribeView(APIView):
    """
    API to handle unsubscription.
    Sets subscribed=False for the user and blacklists in Netcore.
    """
    def post(self, request):
        serializer = UnsubscribeSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user_exists = False
            try:
                user = User.objects.get(email=email)
                user.subscribed = False
                user.save(update_fields=['subscribed'])
                user_exists = True
            except User.DoesNotExist:
                pass

            # Async blacklist in Netcore (even if user not in system)
            blacklist_netcore.delay(email)

            msg = 'Unsubscribed successfully from marketing notifications.'
            if not user_exists:
                msg += ' (Email not found in user system, but blacklisted in Netcore).'

            return Response({'message': msg}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateCampaignView(APIView):
    """
    API for admins to create a marketing campaign.
    Automatically schedules the send task via Celery.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        # Ensure scheduled_at is in future
        data = request.data.copy()
        if 'scheduled_at' in data and timezone.now() > timezone.datetime.fromisoformat(data['scheduled_at']):
            return Response({'error': 'Scheduled time must be in the future.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MarketingCampaignSerializer(data=data)
        if serializer.is_valid():
            campaign = serializer.save()
            # Schedule async task
            send_marketing_campaign.apply_async(args=[campaign.id], eta=campaign.scheduled_at)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
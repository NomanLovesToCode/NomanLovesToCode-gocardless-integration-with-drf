from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .models import *
from .serializers import *

from drf_spectacular.utils import extend_schema, OpenApiResponse


# Create your views here.

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.db import transaction

from .models import *
from .serializers import UserProfileSerializer

from drf_spectacular.utils import extend_schema, OpenApiResponse

# Create your views here.

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=["User Profile"],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'employment_status': {
                        'type': 'string',
                        'enum': ['employed', 'retired', 'volunteer'],
                        'example': 'employed'
                    },
                    'job_details': {
                        'type': 'string',
                        'enum': ['ambulance_service', 'apha', 'blood_bike', 'dental_practice'],
                        'example': 'ambulance_service'
                    },
                    'employer': {
                        'type': 'string',
                        'enum': ['ambulance_service', 'fire_service', 'hm_coustguard', 'independent_lifeboat', 'nhs', 'police', 'red_cross', 'rnli', 'search_and_rescue'],
                        'example': 'ambulance_service'
                    },
                    'id_card_front': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Upload front side of ID card'
                    },
                    'id_card_back': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Upload back side of ID card'
                    },
                    'address_line1': {
                        'type': 'string',
                        'example': '123 Main St'
                    },
                    'address_line2': {
                        'type': 'string',
                        'example': 'Apt 4B'
                    },
                    'city': {
                        'type': 'string',
                        'example': 'Springfield'
                    },
                    'country': {
                        'type': 'string',
                        'example': 'USA'
                    },
                    'postcode': {
                        'type': 'string',
                        'example': '12345'
                    }
                }
            }
        },
        responses={
            200: OpenApiResponse(description="Profile updated successfully"),
            400: OpenApiResponse(description="Invalid data"),
            500: OpenApiResponse(description="An error occurred")
        },
        summary="Update user profile (professional details)",
        description="Update professional details for the authenticated user's profile.",
    )
    def post(self, request):
        try:
            with transaction.atomic():  # Use atomic for safe updates
                user = request.user
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created:
                    # If somehow no profile exists (edge case), but this shouldn't happen post-registration
                    return Response({"detail": "Profile created"}, status=status.HTTP_201_CREATED)
                
                serializer = UserProfileSerializer(
                    instance=profile, 
                    data=request.data, 
                    context={'request': request}, 
                    partial=True
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {"detail": "Profile updated successfully", "profile": serializer.data},
                        status=status.HTTP_200_OK
                    )
                
                return Response(
                    {"detail": "Invalid data", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"detail": "An error occurred", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["User Profile"],
        responses={
            200: UserProfileSerializer,
            404: OpenApiResponse(description="Profile not found"),
            500: OpenApiResponse(description="An error occurred")
        },
        summary="Retrieve user profile",
        description="Get the authenticated user's profile details.",
    )
    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": "An error occurred", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
            
class BasicProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=["User Profile"],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'first_name': {
                        'type': 'string',
                        'example': 'John'
                    },
                    'last_name': {
                        'type': 'string',
                        'example': 'Doe'
                    },
                    'profile_picture': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Upload profile picture'
                    }
                }
            }
        },
        responses={
            200: OpenApiResponse(description="Basic profile updated successfully"),
            400: OpenApiResponse(description="Invalid data"),
            500: OpenApiResponse(description="An error occurred")
        },
        summary="Update basic profile (name and picture)",
        description="Update first name, last name, and profile picture for the authenticated user.",
    )
    def post(self, request):
        try:
            with transaction.atomic():
                user = request.user
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created:
                    return Response({"detail": "Profile created"}, status=status.HTTP_201_CREATED)
                
                serializer = BasicProfileSerializer(
                    instance=profile, 
                    data=request.data, 
                    context={'request': request}, 
                    partial=True
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {"detail": "Basic profile updated successfully", "profile": serializer.data},
                        status=status.HTTP_200_OK
                    )
                
                return Response(
                    {"detail": "Invalid data", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"detail": "An error occurred", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["User Profile"],
        responses={
            200: BasicProfileSerializer,
            404: OpenApiResponse(description="Profile not found"),
            500: OpenApiResponse(description="An error occurred")
        },
        summary="Retrieve basic profile",
        description="Get the authenticated user's basic profile details (name and picture).",
    )
    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = BasicProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": "An error occurred", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
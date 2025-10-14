from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

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
        },
    },
            responses= {201: OpenApiResponse(description="Profile created successfully"),
                       400: OpenApiResponse(description="Invalid data"),
                       500: OpenApiResponse(description="An error occurred")},
            summary="Create a user profile",
            description="Create a user profile for the authenticated user.",
        )
    def post(self, request):
       
        try:
                
            profile = UserProfileSerializer(data=request.data, context={'request': request})
            if profile.is_valid():
                profile.save()
                return Response(
                    {"detail": "Profile created successfully", "profile": profile.data},
                    status=status.HTTP_201_CREATED
                    )
            
            return Response(
                {"detail": "Invalid data", "errors": profile.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "An error occurred", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
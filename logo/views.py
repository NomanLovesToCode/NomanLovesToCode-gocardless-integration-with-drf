from django.shortcuts import render
from .serializers import CompanyLogoSerializer
from .models import CompanyLogo

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from custom_permissions.admin_permission import IsAdminOrReadOnly

from drf_spectacular.utils import extend_schema, OpenApiResponse

# Create your views here.


class CompanyLogoView(APIView):
    serializer_class = CompanyLogoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    
    @extend_schema(
        tags=['logo'],
        request=CompanyLogoSerializer,
        responses={
            201: OpenApiResponse(description="Logo uploaded successfully"),
            400: OpenApiResponse(description="Validation failed (e.g., invalid image)"),
        },
        description="Upload a company logo (admin-only). Overwrites if one exists.",
        summary="Upload Company Logo",
    )
    def post(self,request):
        serializer = CompanyLogoSerializer(data=request.data)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            
            return Response(
                {"detail":"Logo uploaded sucessfully",
                 "data":serializer.data
                 },
                status = status.HTTP_201_CREATED
            )
            
        return Response(
            {"detail":"Failed logo upload"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    
    def get(self,request):
        try:
            logo = CompanyLogo.objects.all().first()
            
            serializer = CompanyLogoSerializer(logo)
            
            return Response(
                {"detail":"Success",
                 "data":serializer.data},
                status=status.HTTP_200_OK
            )
        except CompanyLogo.DoesNotExist:
            return Response(
                {"detail":"Failed!"},
                status=status.HTTP_404_NOT_FOUND
            )
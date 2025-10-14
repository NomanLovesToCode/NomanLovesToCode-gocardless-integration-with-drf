from django.shortcuts import render
from .serializers import CompanyLogoSerializer
from .models import CompanyLogo

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from custom_permissions.admin_permission import IsAdminOrReadOnly
# Create your views here.


class CompanyLogoView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    def post(self,request):
        serializer = CompanyLogoSerializer(data=request.data)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            
            return Response(
                {"detail":"Logo uploaded sucessfully"},
                status = status.HTTP_201_CREATED
            )
            
        return Response(
            {"detail":"Failed logo upload"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    
    def get(self,request):
        try:
            logo = CompanyLogo.objects.get.all().first()
            
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
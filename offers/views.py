# views.py
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q

from .models import Category,SubCategory, Offer
from .serializers import CategorySerializer, OfferSerializer
from custom_permissions.retailer_permission import IsOwner
from custom_permissions.user_subscribed_permission import IsSubscribed


class CategoryListView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=["Offers"],
        responses={
            200: CategorySerializer(many=True),
            404: OpenApiResponse(description="No categories found")
        },
        summary="Fetch all categories with their subcategories and products",
        description="Retrieve a list of all categories, each with their associated subcategories and products.",
    )
    def get(self, request):
        categories = Category.objects.prefetch_related(
            "subcategories__products"
        ).all()
        
        if not categories.exists():
            return Response(
                {"detail": "No category created yet."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CategorySerializer(categories, many=True)
        
        return Response(
            {
                "detail": "Categories fetched successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class CategoryDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=["Offers"],
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category not found")
        },
        summary="Fetch a single category with subcategories and products",
        description="Retrieve a specific category by slug with all associated subcategories and products.",
    )
    def get(self, request, slug):
        category = get_object_or_404(
            Category.objects.prefetch_related("subcategories__products"),
            slug=slug
        )
        
        serializer = CategorySerializer(category)
        return Response(
            {   
                "detail": "Category fetched successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class OfferDetailView(APIView):
    permission_classes = [ IsOwner, IsSubscribed ]
    
    @extend_schema(
        tags=["Offers"],
        responses={
            200: OfferSerializer,
            404: OpenApiResponse(description="Offer not found")
        },
        summary="Fetch a single offer by slug",
        description="Retrieve a specific offer by its slug. Requires authentication and ownership.",
    )
    def get(self, request, slug):
        offer = get_object_or_404(Offer, slug=slug, is_active=True)
        
        # Check ownership permission
        self.check_object_permissions(request, offer)
        
        serializer = OfferSerializer(offer)
        return Response(
            {
                "detail": "Offer fetched successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        



class OfferSearchView(APIView):
    permission_classes=[ IsSubscribed ]
    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"offers": []})

        # Direct matches on Offer fields
        offers = Offer.objects.filter(
            Q(brand_name__icontains=query) |
            Q(coupon_code__icontains=query) |
            Q(description__icontains=query)
        )

        # Category matches
        category_matches = Category.objects.filter(name__icontains=query)
        if category_matches.exists():
            offers = offers | Offer.objects.filter(subcategory__category__in=category_matches)

        # SubCategory matches
        subcategory_matches = SubCategory.objects.filter(name__icontains=query)
        if subcategory_matches.exists():
            offers = offers | Offer.objects.filter(subcategory__in=subcategory_matches)

        offers = offers.distinct()

        serializer = OfferSerializer(offers, many=True)
        return Response({"offers": serializer.data})

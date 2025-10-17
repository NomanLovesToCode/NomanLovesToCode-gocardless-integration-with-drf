from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q

from .models import *
from .serializers import *
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
            "subcategories__offers"
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
    def get(self, request, pk):
        category = get_object_or_404(
            Category.objects.prefetch_related("subcategories__offers"),
            pk=pk
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
    def get(self, request, pk):
        offer = get_object_or_404(Offer, pk=pk, is_active=True)
        
        if not offer.is_valid():
            
            return Response (
                {
                    'detail': "This offer has been expired!",
                    'status': status.HTTP_403_FORBIDDEN
                }
            )
        
        
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





class VoucherDetailView(APIView):
    # Permission class is by default IsAuthenticated
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        tags=["Voucher"],
        responses={
            200: VoucherSerializer,
            404: OpenApiResponse(description="Voucher not found")
        },
        summary="Fetch a single voucher by offer id",
        description="Retrieve a specific voucher for the offer by its id. Requires authentication.",
    )
    def get(self, request,pk): # It is the primary key or id of the related offer
        
        offer = get_object_or_404(Offer, pk=pk, is_active=True)
        
        if not offer.is_valid():
            if offer.is_active:
                offer.is_active = False
                offer.save()                    
            
            return Response (
                {
                    'detail': "This offer has been expired!",
                    'status': status.HTTP_403_FORBIDDEN
                }
            )
        
        # getting all the vouchers those are of this offer and not claimed by any user
        vouchers = Voucher.objects.filter(offer=offer, claimed=False, claimed_by=None)
        
        if not vouchers.exists():
            return Response (
                {
                    'error': 'Sorry! No voucher left for this offer',
                    'status': status.HTTP_404_NOT_FOUND
                }
            )
        
        now = timezone.now()
        
        # Vouchers of this offer claimed by this user
        try:
            last_claimed_voucher = Voucher.objects.filter(offer=offer, claimed=True, claimed_by=request.user).order_by('-claimed_at').get()
        except Voucher.DoesNotExist:
            # Since the user didn't claimed any voucher.He gets an unclaimed voucher of this offer
            
            voucher = vouchers[0]
            voucher.claimed = True
            voucher.claimed_by = request.user
            voucher.claimed_at = now
            voucher.save()
            
            # Since the voucher is claimed assign the voucher in Voucher Reservation Log model
            
            VoucherReservationLog.objects.create(user=request.user, voucher=voucher, claimed_at=now)
            
            serializer = VoucherSerializer(voucher)
            return Response(
                {
                    "detail": "Voucher data fetched successfully!",
                    "data":serializer.data 
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response (
                {
                    'details': e,
                    'status': status.HTTP_400_BAD_REQUEST
                }
            )
            
        
        # since the user claimed voucher of this offer and the time has passed the offer's cooldown time he can claim a new one.
        cooldown_hours = last_claimed_voucher.offer.voucher_cooldown_hours
        cooldown_delta = timedelta(hours=cooldown_hours)
        if now >= (last_claimed_voucher.claimed_at + cooldown_delta):
            
            voucher = vouchers[0]
            voucher.claimed = True
            voucher.claimed_by = request.user
            voucher.claimed_at = timezone.now()
            voucher.save()
            
            # Storing this voucher as claimed in Voucher Reservation model
            VoucherReservationLog.objects.create(user=request.user, voucher=voucher, claimed_at=voucher.claimed_at)
            
            serializer = VoucherSerializer(voucher)
            
            return Response (
                {
                    'details': 'Your new coupon code is here',
                    'data': serializer.data
                }
            )                   
            
        else:
            
            # Since the cooldown time hasn't end the user shall see his last claimed voucher
            remaining = (last_claimed_voucher.claimed_at + cooldown_delta) - now
            hours_remaining = int(remaining.total_seconds() / 3600)  # simple remaining hours
            
            serializer = VoucherSerializer(last_claimed_voucher)
            
            return Response (
                {
                    'details': f'You must wait for another {hours_remaining} hours to claim new coupon code',
                    'data': serializer.data
                }
            )
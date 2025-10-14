from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static 
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from subscriptions.views import RootHandler  # NEW: Import root handler


admin.site.site_header = "Administration"
admin.site.site_title = "Welcome to Admin Site"



urlpatterns = [
    
    path('', RootHandler.as_view(), name='root'),
    
    path("admin/", admin.site.urls),

    # App routes
    path("api/accounts/", include("accounts.urls")),
    path("api/offers/", include("offers.urls")),
    path("api/profiles/", include("user_profile.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/subscriptions/", include("subscriptions.urls")),
    path("api/logo/", include("logo.urls")),

    # API schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Redoc
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

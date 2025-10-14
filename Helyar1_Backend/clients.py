from django.conf import settings
import gocardless_pro

def get_gocardless_client():
    access_token = getattr(settings, 'GC_ACCESS_TOKEN')
    environment = getattr(settings, 'GC_ENVIRONMENT', 'sandbox')  # Default to sandbox
    
    if not access_token:
        raise ValueError("GC ACCESS TOKEN is not found")
    
    # Validate token matches environment
    if environment == 'sandbox' and not access_token.startswith('sandbox_'):
        raise ValueError(f"Sandbox environment requires a sandbox token (starts with 'sandbox_')")
    elif environment == 'live' and not access_token.startswith('live_'):
        raise ValueError(f"Live environment requires a live token (starts with 'live_')")
    
    client = gocardless_pro.Client(
        access_token=access_token,
        environment=environment
    )
    
    return client

gocardless_client = get_gocardless_client()
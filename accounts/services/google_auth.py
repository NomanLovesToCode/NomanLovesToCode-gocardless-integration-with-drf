import random
import string
from urllib.parse import urlencode
import requests
from django.conf import settings
from django.urls import reverse_lazy

class GoogleAuthService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(self):
        self.redirect_uri = f"{settings.BASE_BACKEND_URL or 'http://localhost:8000'}{reverse_lazy('accounts:google-callback')}"

    def get_auth_url(self):
        state = ''.join(random.choices(string.ascii_letters + string.digits, k=32))  # CSRF protection
        params = {
            'response_type': 'code',
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPES),
            'state': state,
            'access_type': 'offline',
            'prompt': 'select_account',
        }
        auth_url = f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
        return auth_url, state  # Store state in session for callback

    def get_user_from_code(self, code, state):
        # Verify state (from session) to prevent CSRF
        if not state:  # In real app, get from request.session
            raise ValueError("Invalid state")

        # Exchange code for tokens
        token_data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
        }
        token_response = requests.post(self.GOOGLE_TOKEN_URL, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()

        # Fetch user info
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        user_response = requests.get(self.GOOGLE_USER_INFO_URL, headers=headers)
        user_response.raise_for_status()
        google_user = user_response.json()

        return {
            'email': google_user.get('email'),
            'first_name': google_user.get('given_name'),
            'last_name': google_user.get('family_name'),
            'verified': google_user.get('email_verified', False),
        }
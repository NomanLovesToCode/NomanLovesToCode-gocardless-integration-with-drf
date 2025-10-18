from pathlib import Path
import os
import environ

env = environ.Env(
    DEBUG=(bool, False)  # default False if not set
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=['127.0.0.1', 'localhost']) + ['lelia-leafed-lashandra.ngrok-free.dev']


# Application definition

INSTALLED_APPS = [
    #'jazzmin',  # For Admin UI Customization
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    
    #Local Apps
    'accounts.apps.AccountsConfig',
    'offers.apps.OffersConfig',
    'user_profile.apps.UserProfileConfig',
    'notifications.apps.NotificationsConfig',
    'subscriptions.apps.SubscriptionsConfig',
    'logo.apps.LogoConfig',
    'user_consent.apps.UserConsentConfig',
    
    #Third-Party Apps
    'django_cleanup.apps.CleanupConfig', # For cleaning up old files
    'rest_framework',
    'rest_framework_simplejwt', # For JWT Authentication
    'rest_framework_simplejwt.token_blacklist', # For Blacklisting Refresh Tokens
    'drf_spectacular', # For Automated documentation OpenAPI 3.0
    'drf_spectacular_sidecar', # To support spectacular when it will be deployed on production
    'django_celery_beat', # For celery
    'corsheaders', # To connect to the frontend
]


AUTH_USER_MODEL='accounts.User'


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Helyar1_Backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 'logo.context_processors.site_settings', # came from context processors.py files site_settings function to change admin panel logo
            ],
        },
    },
]

WSGI_APPLICATION = 'Helyar1_Backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'


#MEDIA FILES (User Uploaded Content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# ============================================================================
# DRF SPECTACULAR SETTINGS
# ============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Helyar1 Project API Documentation',
    'DESCRIPTION': 'drf-spectacular generated API documentation for Helyar1 Project',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',  # shorthand to use the sidecar instead
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    'TAGS': [
        {'name': 'accounts'},
        {'name': 'subscriptions'},
        {'name': 'offers'},
    ],
}


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module}:{lineno} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'project.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'webhook_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'webhooks.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'subscriptions': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'subscriptions.webhooks': {
            'handlers': ['webhook_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gocardless_pro': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
}


# ============================================================================
# SESSION CONFIGURATION (Enhanced for GoCardless)
# ============================================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# IMPORTANT: Make SECURE conditional based on environment
ENVIRONMENT = env('ENVIRONMENT', default='development')
if ENVIRONMENT == 'production' or 'ngrok' in str(ALLOWED_HOSTS):
    SESSION_COOKIE_SECURE = True
else:
    SESSION_COOKIE_SECURE = False  # For local development

SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks


# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

EMAIL_BACKEND = env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")


# ============================================================================
# PHONE NUMBER VALIDATION
# ============================================================================

PHONE_NUMBER_VALIDATION_API_KEY = env("PHONE_NUMBER_VALIDATION_API_KEY")


# ============================================================================
# JWT CONFIGURATION
# ============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,  # Use SECRET_KEY from settings
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(days=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=30),
}


# ============================================================================
# GOCARDLESS CONFIGURATION
# ============================================================================

GC_ACCESS_TOKEN = env('GC_ACCESS_TOKEN')
GC_PUBLISHABLE_KEY = env('GC_PUBLISHABLE_KEY', default='')
GC_WEBHOOK_SECRET = env('GC_WEBHOOK_SECRET')
GC_ENVIRONMENT = env('GC_ENVIRONMENT', default='sandbox')

ENVIRONMENT = env('ENVIRONMENT', default='development')

# Base URLs for redirects (make environment-aware)
if ENVIRONMENT == 'production':
    BASE_FRONTEND_URL = env('FRONTEND_URL', default='https://yourdomain.com')
    BASE_BACKEND_URL = env('BACKEND_URL', default='https://api.yourdomain.com')
else:
    # Development/ngrok
    BASE_FRONTEND_URL = env('FRONTEND_URL', default='https://lelia-leafed-lashandra.ngrok-free.dev')
    BASE_BACKEND_URL = env('BACKEND_URL', default='https://lelia-leafed-lashandra.ngrok-free.dev')


# ============================================================================
# NETCORE API SETUP
# ============================================================================

NETCORE_CE_API_KEY = env('NETCORE_CE_API_KEY')
NETCORE_EMAIL_API_KEY = env('NETCORE_EMAIL_API_KEY')
FROM_EMAIL = env('FROM_EMAIL')


# ============================================================================
# TWILIO CONFIGURATION
# ============================================================================

TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER')


# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = env.list('CELERY_ACCEPT_CONTENT', default=['json'])
CELERY_TASK_SERIALIZER = env('CELERY_TASK_SERIALIZER', default='json')
CELERY_RESULT_SERIALIZER = env('CELERY_RESULT_SERIALIZER', default='json')
CELERY_TIMEZONE = env('CELERY_TIMEZONE', default='UTC')

# Celery Beat Scheduler
CELERY_BEAT_SCHEDULER = env('CELERY_BEAT_SCHEDULER', default='django_celery_beat.schedulers:DatabaseScheduler')

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-expired-subscriptions': {
        'task': 'subscriptions.tasks.check_expired_subscriptions',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight UTC
    },
    'send-expiry-reminders': {
        'task': 'subscriptions.tasks.send_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM UTC
    },
    'cleanup-pending-subscriptions': {
        'task': 'subscriptions.tasks.cleanup_pending_subscriptions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
}


# ============================================================================
# GOOGLE LOGIN SETUP
# ============================================================================

GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = env('GOOGLE_CLIENT_SECRET', default='')


# ============================================================================
# CORS CONFIGURATION (Uncomment if using separate frontend)
# ============================================================================

# INSTALLED_APPS += ['corsheaders']
# MIDDLEWARE.insert(1, 'corsheaders.middleware.CorsMiddleware')  # Add near top of middleware

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://lelia-leafed-lashandra.ngrok-free.dev",
    BASE_FRONTEND_URL,
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# ============================================================================
# SECURITY SETTINGS (Uncomment for production)
# ============================================================================

# if ENVIRONMENT == 'production':
#     SECURE_SSL_REDIRECT = True
#     SECURE_HSTS_SECONDS = 31536000  # 1 year
#     SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#     SECURE_HSTS_PRELOAD = True
#     SECURE_CONTENT_TYPE_NOSNIFF = True
#     SECURE_BROWSER_XSS_FILTER = True
#     X_FRAME_OPTIONS = 'DENY'
#     CSRF_COOKIE_SECURE = True
#     SESSION_COOKIE_SECURE = True


# ============================================================================
# JAZZMIN UI CUSTOMIZATION (Optional - Uncomment if using)
# ============================================================================

# JAZZMIN_UI_TWEAKS = {
#     "theme": "darkly",
# }

# JAZZMIN_SETTINGS = {
#     "site_title": "Helyar1 Admin",
#     "site_header": "Helyar1 Administration",
#     "welcome_sign": "Welcome to Helyar1 Admin Panel",
#     "site_logo": "logos/admin.png",
#     "site_logo_classes": "img-circle",
#     "site_icon": None,
#     "copyright": "Helyar1 Ltd",
# }
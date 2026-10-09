import os
from pathlib import Path
import tempfile
import cloudinary
import dj_database_url
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Security Settings
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY', 'django-insecure-vishwabharti-college-event-key'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['.vercel.app', '127.0.0.1', 'localhost', '*']

# Installed Apps
INSTALLED_APPS = [
    # Standard Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # 📌 Staticfiles placed before Cloudinary
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    # Vishwabharti CEM Apps
    'accounts',
    'students',
    'events',
    'attendance',
    'certificates',
    'teachers',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CEM.urls'
WSGI_APPLICATION = 'CEM.wsgi.application'

# 📌 Optimized HTML Templates Config
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

# Custom User Model Registration
AUTH_USER_MODEL = 'accounts.User'

# ------------------------------------------------------------------
# 📌 Database Connection (Supabase / PostgreSQL with SQLite fallback)
# ------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,  # ⚡ Keeps DB connection alive across serverless hits
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
        )
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.MinimumLengthValidator'
        )
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.CommonPasswordValidator'
        )
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.NumericPasswordValidator'
        )
    },
]

# Time Zone for India
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static Files Settings
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')

# ------------------------------------------------------------------
# 📌 Cross-Platform Media & Temp Directory (Windows + Vercel Fix)
# ------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(tempfile.gettempdir(), 'media')
FILE_UPLOAD_TEMP_DIR = tempfile.gettempdir()

os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(FILE_UPLOAD_TEMP_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 📸 Cloudinary Storage Settings
# ------------------------------------------------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True,
)

# ⚡ Compressed Static Files & Cloudinary Media Backend
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),  # ⚡ Fast CDN caching
    },
}

# ⚡ Long-term browser caching for static assets (1 Year)
WHITENOISE_MAX_AGE = 31536000

# ------------------------------------------------------------------
# ⚡ High Performance In-Memory Caching (LocMemCache)
# ------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'vishwabharti-cem-cache',
        'TIMEOUT': 300,  # 5 minutes
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_redirect'
LOGOUT_REDIRECT_URL = 'login'

# ------------------------------------------------------------------
# 📌 Email Configuration (Gmail SMTP)
# ------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', EMAIL_HOST_USER
)
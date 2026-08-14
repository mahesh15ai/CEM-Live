import os
import tempfile
from pathlib import Path
import dj_database_url
import cloudinary

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = 'django-insecure-vishwabharti-college-event-key'
DEBUG = True
ALLOWED_HOSTS = ['.vercel.app', '127.0.0.1', 'localhost', '*']

# Installed Apps
INSTALLED_APPS = [
    # Standard Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    # 📌 staticfiles la cloudinary_storage chya aadhi theva
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CEM.urls'
WSGI_APPLICATION = 'CEM.wsgi.application'

# HTML Templates Config
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
# 📌 Supabase Database Connection (With Maheshmahi150904)
# ------------------------------------------------------------------
DATABASE_URL = "postgresql://postgres.uzlhvmcghcdzeyxqqebs:Maheshmahi150904@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,
        ssl_require=True
    )
}

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
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
# 📸 Cloudinary Permanent Storage Settings
# ------------------------------------------------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'hhnkhoen',
    'API_KEY': '977119757646888',
    'API_SECRET': 's-HAROLo9zUq1kvO_LOw57qZJdA'
}

cloudinary.config(
    cloud_name='hhnkhoen',
    api_key='977119757646888',
    api_secret='s-HAROLo9zUq1kvO_LOw57qZJdA',
    secure=True
)

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_redirect'
LOGOUT_REDIRECT_URL = 'login'

# 📌 Email Configuration (Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tsome8522@gmail.com'
EMAIL_HOST_PASSWORD = 'oittzkqatsynbhcd'
DEFAULT_FROM_EMAIL = 'tsome8522@gmail.com'
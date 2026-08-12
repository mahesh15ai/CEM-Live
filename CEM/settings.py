import os
from pathlib import Path
import dj_database_url

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
    'django.contrib.staticfiles',

    # Vishwabharti CEM Apps
    'accounts',
    'students',
    'events',
    'attendance',
    'certificates',
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

# 📌 Supabase Transaction Pooler (Port 6543 - Max Connections Fix)
DATABASE_URL = "postgresql://postgres.uzlhvmcghcdzeyxqqebs:Maheshmahi150904@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,  # Serverless Vercel साठी कनेक्शन तात्काळ बंद करणे आवश्यक आहे
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

# Static Files Settings for Vercel
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Static Output Directory for Vercel Build Process
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 📌 Media Files Settings (Vercel Read-Only System Fix)
MEDIA_URL = '/media/'

if os.environ.get('VERCEL') or os.path.exists('/var/task'):
    MEDIA_ROOT = Path('/tmp/media')
else:
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
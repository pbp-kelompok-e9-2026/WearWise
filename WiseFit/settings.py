import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Deployment mode: strip() also handles accidental spaces in PWS Environs.
PRODUCTION = os.getenv("PRODUCTION", "False").strip().lower() == "true"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY belum diatur di environment variables")

# Never expose Django's detailed error page in production.
DEBUG = False if PRODUCTION else (
    os.getenv("DEBUG", "True").strip().lower() == "true"
)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "zidan-fauzan-wearwise.pws.cs.ui.ac.id"]
CSRF_TRUSTED_ORIGINS = ["https://zidan-fauzan-wearwise.pws.cs.ui.ac.id"]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
    'wardrobe',        # Modul 1
    'worth_to_buy_analyzer.apps.WorthToBuyAnalyzerConfig',    # Modul 2
    'carbon_footprint', # Modul 3
    'lifecycle',       # Modul 4
    'dashboard',       # Modul 5
    'seed_data',
]

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

ROOT_URLCONF = 'WiseFit.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'WiseFit.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Database configuration
if PRODUCTION:
    # Normalize text fields to avoid accidental leading/trailing spaces
    # in PWS Environs (especially DB_HOST and PRODUCTION).
    db_name = os.getenv("DB_NAME", "").strip()
    db_user = os.getenv("DB_USER", "").strip()
    db_password = os.getenv("DB_PASSWORD", "")  # Preserve password exactly.
    db_host = os.getenv("DB_HOST", "").strip()
    db_port = os.getenv("DB_PORT", "5432").strip() or "5432"
    db_schema = os.getenv("SCHEMA", "public").strip() or "public"

    missing_vars = [
        name
        for name, value in {
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
            "DB_HOST": db_host,
        }.items()
        if not value
    ]

    if missing_vars:
        raise RuntimeError(
            "Environment variables database belum lengkap: "
            + ", ".join(missing_vars)
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "OPTIONS": {
                "options": f"-c search_path={db_schema}",
                "connect_timeout": 10,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LOGIN_URL = "main:login"
LOGIN_REDIRECT_URL = "main:show_main"
LOGOUT_REDIRECT_URL = "main:login"

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_USE_FINDERS = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CLIMATIQ_API_KEY = os.environ.get("CLIMATIQ_API_KEY", "")
CLIMATIQ_DATA_VERSION = "^38"

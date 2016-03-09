# Django settings for mash project.

################################################################################
# The MASH web application contains the source code of all the servers
# in the "computation farm" of the MASH project (http://www.mash-project.eu),
# developed at the Idiap Research Institute (http://www.idiap.ch).
#
# Copyright (c) 2016 Idiap Research Institute, http://www.idiap.ch/
# Written by Philip Abbet (philip.abbet@idiap.ch)
#
# This file is part of the MASH web application (mash-web).
#
# The MASH web application is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
#
# The MASH web application is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the MASH web application. If not, see
# <http://www.gnu.org/licenses/>.
################################################################################


import os


####################################################################################################
#
# GENERAL SETTINGS
#
####################################################################################################

ADMINS = (
    ('NAME', 'E-MAIL ADDRESS'),
)

MANAGERS        = ADMINS

TIME_ZONE       = 'Europe/Zurich'   # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
LANGUAGE_CODE   = 'en-us'           # See http://www.i18nguy.com/unicode/language-identifiers.html
SITE_ID         = 1
USE_I18N        = False
SECRET_KEY      = 'u02zt3@rj$$lb!dhru_$sxo8st!#n3vp*vjzig8*9obs@wazk&'

# Absolute path to the root folder of the project
PROJECT_ROOT = ''

DEVELOPMENT_SERVER = True

if DEVELOPMENT_SERVER:
    WEBSITE_URL_DOMAIN          = 'http://localhost:8000'
    FORUM_URL_DOMAIN            = 'http://localhost'
    SECURED_WEBSITE_URL_DOMAIN  = 'https://localhost:8000'
    SECURED_FORUM_URL_DOMAIN    = 'https://localhost'
    DEBUG                       = True
else:
    WEBSITE_URL_DOMAIN          = ''
    FORUM_URL_DOMAIN            = WEBSITE_URL_DOMAIN
    SECURED_WEBSITE_URL_DOMAIN  = WEBSITE_URL_DOMAIN
    SECURED_FORUM_URL_DOMAIN    = FORUM_URL_DOMAIN
    DEBUG                       = False

TEMPLATE_DEBUG = DEBUG


####################################################################################################
#
# DATABASE
#
####################################################################################################

DATABASE_ENGINE             = 'mysql'       # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME               = ''            # Or path to database file if using sqlite3.
DATABASE_USER               = ''            # Not used with sqlite3.
DATABASE_PASSWORD           = ''            # Not used with sqlite3.
DATABASE_HOST               = ''            # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT               = ''            # Set to empty string for default. Not used with sqlite3.
DATABASE_PHPBB_PREFIX       = 'phpbb_'
DATABASE_MEDIAWIKI_PREFIX   = 'mw_'

if os.getenv('MASH_TEST_MODE', None) == 'ON':
    DATABASE_NAME += '-test'


####################################################################################################
#
# MEDIA
#
####################################################################################################

MEDIA_ROOT                  = PROJECT_ROOT + 'media'    # Absolute path to the directory that holds media
MEDIA_URL                   = WEBSITE_URL_DOMAIN        # URL that handles the media served from MEDIA_ROOT
ADMIN_MEDIA_PREFIX          = '/media/'                 # URL prefix for admin media -- CSS, JavaScript and images
STATIC_DOC_ROOT             = PROJECT_ROOT + 'media'
LOG_FILES_ROOT              = PROJECT_ROOT + 'logs'
INSTRUMENTS_ROOT            = PROJECT_ROOT + 'instruments'
DATA_REPORTS_ROOT           = PROJECT_ROOT + 'data'
HEURISTICS_DEBUGGING_ROOT   = PROJECT_ROOT + 'debugging'
MODELS_ROOT                 = PROJECT_ROOT + 'models'
SNIPPETS_ROOT               = STATIC_DOC_ROOT + '/snippets'
FORUM_ROOT                  = PROJECT_ROOT + 'forum'

if os.getenv('MASH_TEST_MODE', None) == 'ON':
    DATA_REPORTS_ROOT   = 'data'
    MODELS_ROOT         = 'models'


####################################################################################################
#
# GIT REPOSITORIES
#
####################################################################################################

REPOSITORIES_ROOT           = PROJECT_ROOT + 'repositories/'    # Absolute path to the directory that holds the repositories

if os.getenv('MASH_TEST_MODE', None) == 'ON':
    REPOSITORIES_ROOT = 'repositories/'

REPOSITORY_HEURISTICS       = 'heuristics.git'
REPOSITORY_UPLOAD           = 'upload.git'
REPOSITORY_HEURISTICS_URL   = REPOSITORIES_ROOT + REPOSITORY_HEURISTICS
REPOSITORY_UPLOAD_URL       = REPOSITORIES_ROOT + REPOSITORY_UPLOAD
COMMIT_AUTHOR               = 'MASH <mash@mash-project.eu>'


####################################################################################################
#
# SCHEDULER
#
####################################################################################################

SCHEDULER_ADDRESS   = '127.0.0.1'
SCHEDULER_PORT      = 14000


####################################################################################################
#
# ACCOUNTS
#
####################################################################################################

AUTH_PROFILE_MODULE                 = 'accounts.UserProfile'
ACCOUNT_ACTIVATION_DAYS             = 2
ACCOUNT_REGISTRATION_USE_RECAPTCHA  = False
RECAPTCHA_PUB_KEY                   = ''
RECAPTCHA_PRIVATE_KEY               = ''
SYSTEM_ACCOUNT                      = 'MASH'


####################################################################################################
#
# SSL
#
####################################################################################################

HTTPS_SUPPORT                       = False
SESSION_COOKIE_SECURE               = HTTPS_SUPPORT


####################################################################################################
#
# E-MAILS
#
####################################################################################################

DEFAULT_FROM_EMAIL = 'no-reply@mash-project.eu'
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = '[MASH] '

if not(DEVELOPMENT_SERVER):
    EMAIL_HOST          = ''
    EMAIL_PORT          = 0
    EMAIL_HOST_USER     = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS       = False
else:
    EMAIL_HOST          = 'localhost'
    EMAIL_PORT          = 1025
    EMAIL_HOST_USER     = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS       = False



####################################################################################################
#
# DJANGO MACHINERY
#
####################################################################################################

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.request',
)

if DEBUG:
    TEMPLATE_CONTEXT_PROCESSORS += (
        'django.core.context_processors.debug',
    )


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'mash.sessionprofile.middleware.SessionProfileMiddleware',
    'mash.ssl.middleware.SSLRedirect',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)


ROOT_URLCONF = 'mash.urls'


TEMPLATE_DIRS = (
    PROJECT_ROOT + 'templates',
)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'mash.accounts',
    'mash.classifiers',
    'mash.clustering',
    'mash.contests',
    'mash.downloads',
    'mash.experiments',
    'mash.factory',
    'mash.goalplanners',
    'mash.heuristics',
    'mash.homepage',
    'mash.instruments',
    'mash.logs',
    'mash.menu',
    'mash.news',
    'mash.phpbb',
    'mash.registration',
    'mash.servers',
    'mash.sessionprofile',
    'mash.tasks',
    'mash.texts_db',
    'mash.tools',
    'mash.utils',
    'mash.wiki',
)


# Requires django-logging and django-extensions
# See http://code.google.com/p/django-logging and http://code.google.com/p/django-command-extensions
# Feel free to comment/change these settings 
if DEVELOPMENT_SERVER:
    MIDDLEWARE_CLASSES += (
        'djangologging.middleware.LoggingMiddleware',
        'djangologging.middleware.SuppressLoggingOnAjaxRequestsMiddleware',
    )
    
    try:
        import django_extensions
        INSTALLED_APPS += (
            'django_extensions',
        )
    except:
        pass

    INTERNAL_IPS                = ('127.0.0.1',)
    LOGGING_OUTPUT_ENABLED      = True
    LOGGING_LOG_SQL             = True
    LOGGING_INTERCEPT_REDIRECTS = False
    LOGGING_SHOW_METRICS        = True

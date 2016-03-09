import os, sys

sys.path.append('/local/mash-web')
sys.path.append('/local/mash-web/mash')

os.environ['DJANGO_SETTINGS_MODULE'] = 'mash.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

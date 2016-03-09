# This is a modification of the snippet found at: http://djangosnippets.org/snippets/85/
#################################################################################
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


 released under the Python license, Copyright (C) 2007, Stephen Zabel,
# by Stephen Zabel - sjzabel@gmail.com and Jay Parlar - parlar@gmail.com

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect

SSL = 'SSL'

class SSLRedirect:

    def __init__(self):
        self.enabled = getattr(settings, 'HTTPS_SUPPORT')

    def process_view(self, request, view_func, view_args, view_kwargs):
        secure = None
        if SSL in view_kwargs:
            if self.enabled:
                secure = view_kwargs[SSL]
            del view_kwargs[SSL]

        if (secure is not None) and (secure != self._is_secure(request)):
            return self._redirect(request, secure)

        return None

    def _is_secure(self, request):
        if request.is_secure():
                return True

        # Handle the Webfaction case until this gets resolved in the request.is_secure()
        if 'HTTP_X_FORWARDED_SSL' in request.META:
            return request.META['HTTP_X_FORWARDED_SSL'] == 'on'

        return False

    def _redirect(self, request, secure):
        if secure:
            newurl = "%s%s" % (settings.SECURED_WEBSITE_URL_DOMAIN, request.get_full_path())
        else:
            newurl = "%s%s" % (settings.WEBSITE_URL_DOMAIN, request.get_full_path())

        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError, \
        """Django can't perform a SSL redirect while maintaining POST data.
           Please structure your views so that redirects only occur during GETs."""

        return HttpResponsePermanentRedirect(newurl)

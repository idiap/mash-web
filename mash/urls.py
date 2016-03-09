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


from django.conf.urls.defaults import *
from django.conf import settings


# Enable the admin panel
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^$',                 'mash.homepage.views.index'),
    (r'^accounts/',         include('mash.accounts.urls')),
    url(r'^admin/', include(admin.site.urls)),
    #(r'^admin/(.*)',        admin.site.root),
    (r'^clustering/',       include('mash.clustering.urls')),
    (r'^contests/',         include('mash.contests.urls')),
    (r'^downloads/',        'mash.downloads.views.index'),
    (r'^experiments/',      include('mash.experiments.urls')),
    (r'^heuristics/',       include('mash.heuristics.urls')),
    (r'^factory/',          include('mash.factory.urls')),
    (r'^instrumentation/',  include('mash.instruments.urls')),
    (r'^logs/',             include('mash.logs.urls')),
    (r'^news/',             include('mash.news.urls')),
    (r'^servers/',          include('mash.servers.urls')),
    (r'^tools/',            include('mash.tools.urls')),
)


if settings.DEVELOPMENT_SERVER:
    urlpatterns += patterns('',
        (r'^css/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/css'}),
        (r'^ace/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/ace'}),
        (r'^video/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/video'}),
        (r'^images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/images'}),
        (r'^js/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/js'}),
        (r'^files/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/files'}),
        (r'^instruments/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/instruments'}),
        (r'^snippets/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT + '/snippets'}),
        (r'^forum/', 'utils.views.redirect_to_domain', {'dest_domain': settings.FORUM_URL_DOMAIN}),
        (r'^wiki/', 'utils.views.redirect_to_domain', {'dest_domain': settings.FORUM_URL_DOMAIN}),
    )


handler500 = 'mash.homepage.views.custom_error_view'

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


urlpatterns = patterns('mash.heuristics.views',
    (r'^$',                                     'heuristics_list'),
    (r'^public/$',                              'public_heuristics_list'),
    (r'^public/(?P<user_id>\d+)/$',             'public_heuristics_list'),
    (r'^private/$',                             'private_heuristics_list', {'SSL': True}),
    (r'^private/(?P<user_id>\d+)/$',            'private_heuristics_list', {'SSL': True}),
    
    (r'^(?P<heuristic_id>\d+)/$',               'heuristic'),
    (r'^v(?P<version_id>\d+)/$',                'heuristic'),

    (r'^view/(?P<author_name>\w+)/(?P<heuristic_name>\w+)/$',                   'heuristic_by_name'),
    (r'^view/(?P<author_name>\w+)/(?P<heuristic_name>\w+)/(?P<version>\d+)/$',  'heuristic_by_name'),

    (r'^edit/(?P<heuristic_id>\d+)/$',          'edit', {'SSL': True}),
    (r'^publish/(?P<version_id>\d+)/$',         'publish', {'SSL': True}),
    (r'^delete/(?P<version_id>\d+)/$',          'delete', {'SSL': True}),
    (r'^topic/(?P<heuristic_id>\d+)/$',         'topic'),

    (r'^upload/$',                              'upload', {'SSL': True}),
    (r'^upload_version/(?P<heuristic_id>\d+)/$','upload_version', {'SSL': True}),
    (r'^status/(?P<version_id>\d+)/$',          'status', {'SSL': True}),
    (r'^test_heuristic_name/$',                 'test_heuristic_name', {'SSL': True}),

    (r'^search/$',                              'search_popup'),
    (r'^search_own/$',                          'search_popup', {'only_own': True, 'SSL': True}),

    (r'^diff/$',                                'diff'),
)

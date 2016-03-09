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
from mash.experiments.models import Configuration


urlpatterns = patterns('mash.experiments.views',
    (r'^$',                                 'public_experiments_list'),
    (r'^consortium/$',                      'consortium_experiments_list', {'SSL': True}),
    (r'^contest/$',                         'contest_experiments_list', {'SSL': True}),
    (r'^private/$',                         'private_experiments_list', {'SSL': True}),
    (r'^private/(?P<user_id>\d+)/$',        'private_experiments_list', {'SSL': True}),

    (r'^(?P<experiment_id>\d+)/$',          'experiment'),

    (r'^schedule/private/$',                'experiments_schedule_private', {'SSL': True}),
    (r'^schedule/consortium/$',             'experiments_schedule_advanced',
                                                {'experiment_type': Configuration.CONSORTIUM, 'SSL': True}),
    (r'^schedule/contest/$',                'experiments_schedule_advanced',
                                                {'experiment_type': Configuration.CONTEST_BASE, 'SSL': True}),

    (r'^cancel/(?P<experiment_id>\d+)/$',   'delete_experiment', {'SSL': True}),
    (r'^delete/(?P<experiment_id>\d+)/$',   'delete_experiment', {'SSL': True}),

    (r'^topic/(?P<experiment_id>\d+)/$',    'topic'),
)

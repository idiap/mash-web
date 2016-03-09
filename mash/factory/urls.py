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


urlpatterns = patterns('mash.factory.views',
    (r'^$',                             'factory', { 'SSL': True }),
    (r'^tasks/$',                       'tasks', { 'SSL': True }),
    (r'^last_recorded_data/$',          'last_recorded_data', { 'SSL': True }),

    (r'^upload/$',                      'upload', { 'SSL': True }),
    (r'^delete/$',                      'delete', { 'SSL': True }),
    (r'^retrieve_source_code/$',        'retrieve_source_code', { 'SSL': True }),

    (r'^test/$',                        'test', { 'SSL': True }),
    (r'^test/(?P<task_number>\d+)/$',   'singleTest', { 'SSL': True }),

    (r'^groups/$',                      'groups', { 'SSL': True }),

    (r'^experiment_activity/$',         'experiment_activity', { 'SSL': True }),

    (r'^menu_status/$',                                                                 'retrieve_menu_status',      { 'SSL': True }),
    (r'^test_results/$',                                                                'test_results',              { 'SSL': True }),
    (r'^test_results_tutorial/$',                                                       'test_results_tutorial',     { 'SSL': True }),
    (r'^task_details/(?P<number>\d+)/$',                                                'task_details',              { 'SSL': True }),
    (r'^task_details_tutorial/(?P<number>\d+)/$',                                       'task_details_tutorial',     { 'SSL': True }),
    (r'^rounds_results/(?P<task_number>\d+)/$',                                         'rounds_results',            { 'SSL': True }),
    (r'^rounds_results_tutorial/(?P<task_number>\d+)/$',                                'rounds_results_tutorial',   { 'SSL': True }),
    (r'^sequence_details/(?P<task>\d+)/(?P<sequence>\d+)/$',                            'sequence_details',          { 'SSL': True }),
    (r'^sequence_details_tutorial/(?P<task>\d+)/(?P<sequence>\d+)/$',                   'sequence_details_tutorial', { 'SSL': True }),
    (r'^recorded_data/(?P<task>\d+)/(?P<sequence>\d+)/$',                               'recorded_data',             { 'SSL': True, 'frame_index': 0 }),
    (r'^recorded_data_tutorial/(?P<task>\d+)/(?P<sequence>\d+)/$',                      'recorded_data_tutorial',    { 'SSL': True, 'frame_index': 0 }),
    (r'^recorded_data/(?P<task>\d+)/(?P<sequence>\d+)/(?P<frame_index>\d+)/$',          'recorded_data',             { 'SSL': True }),
    (r'^recorded_data_tutorial/(?P<task>\d+)/(?P<sequence>\d+)/(?P<frame_index>\d+)/$', 'recorded_data_tutorial',    { 'SSL': True }),
    (r'^record_data/(?P<task>\d+)/(?P<sequence>\d+)/(?P<heuristic>\d+)/$',              'record_data',               { 'SSL': True }),
    (r'^record_data_tutorial/(?P<task>\d+)/(?P<sequence>\d+)/(?P<heuristic>\d+)/$',     'record_data_tutorial',      { 'SSL': True }),
    (r'^snippet/(?P<task>\d+)/(?P<instrument_view>\d+)/$',                              'snippet',                   { 'SSL': True }),
    (r'^snippet_tutorial/(?P<task>\d+)/(?P<instrument_view>\d+)/$',                     'snippet_tutorial',          { 'SSL': True }),
)

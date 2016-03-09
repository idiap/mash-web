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
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views
from django.conf import settings

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
    (r'^$',                             'mash.accounts.views.profile'),
    (r'^login/$',                       'mash.accounts.views.login', {'SSL': True}),
    (r'^logout/$',                      'django.contrib.auth.views.logout', {'next_page': '%s/' % settings.WEBSITE_URL_DOMAIN, 'SSL': True}),

    (r'^profile/$',                     'mash.accounts.views.profile'),
    (r'^profile/(?P<user_id>\d+)/$',    'mash.accounts.views.profile'),
    (r'^profile/f(?P<user_id>\d+)/$',   'mash.accounts.views.forum_profile'),

    (r'^members/$',                     'mash.accounts.views.members'),
    (r'^searchuser/$',                  'mash.accounts.views.members', { 'search_popup': True }),

    (r'^group/create/$',                'mash.accounts.views.group_create'),
    (r'^group/delete/$',                'mash.accounts.views.group_delete'),

    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$', activate, name='registration_activate'),
    url(r'^register/$',                         register, {'SSL': True}, name='registration_register'),
    url(r'^register/complete/$',                direct_to_template, {'template': 'registration/registration_complete.html', 'SSL': True},
                                                name='registration_complete'),

    url(r'^password/change/$',          auth_views.password_change,
                                        {'template_name': 'accounts/password_change.html',
                                          'SSL': True
                                        },
                                        name='auth_password_change'),
    url(r'^password/change/done/$',     auth_views.password_change_done,
                                        {'template_name': 'accounts/password_change_done.html',
                                         'SSL': True
                                        },
                                        name='auth_password_change_done'),

    url(r'^password/reset/$',           auth_views.password_reset,
                                        {'template_name': 'accounts/password_reset.html',
                                         'email_template_name': 'accounts/password_reset_email.txt',
                                         'SSL': True
                                        },
                                        name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                                        auth_views.password_reset_confirm,
                                        {'template_name': 'accounts/password_reset_confirm.html',
                                         'SSL': True
                                        },
                                        name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$',  auth_views.password_reset_complete,
                                        {'template_name': 'accounts/password_reset_complete.html',
                                         'SSL': True
                                        },
                                        name='auth_password_reset_complete'),
    url(r'^password/reset/done/$',      auth_views.password_reset_done,
                                        {'template_name': 'accounts/password_reset_done.html',
                                         'SSL': True
                                        },
                                        name='auth_password_reset_done'),

    (r'^promote/superuser/(?P<user_id>\d+)/$',      'mash.accounts.views.promote_to_superuser', {'SSL': True}),
    (r'^promote/projectmember/(?P<user_id>\d+)/$',  'mash.accounts.views.promote_to_projectmember', {'SSL': True}),
    (r'^promote/contributor/(?P<user_id>\d+)/$',    'mash.accounts.views.promote_to_contributor', {'SSL': True}),
)

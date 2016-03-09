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


from mash.servers.models import *
from django.contrib import admin


class ServerAdmin(admin.ModelAdmin):

    list_display        = ('name', 'address', 'port', 'server_type', 'subtype', 'current_job',
                           'restrict_experiment', 'clustering_algorithm', 'status')
    list_filter         = ['address', 'server_type', 'subtype', 'restrict_experiment', 'clustering_algorithm', 'status']
    search_fields       = ['name', 'address', 'server_type', 'subtype', 'current_job', 'restrict_experiment', 'status']
    list_display_links  = ('name',)

admin.site.register(Server, ServerAdmin)


class JobAdmin(admin.ModelAdmin):

    list_display        = ('__unicode__', 'server', 'heuristic_version', 'experiment', 'status', 'logs')
    list_filter         = ['server', 'status']
    search_fields       = ['server', 'heuristic_version', 'experiment']
    list_display_links  = ('__unicode__',)

admin.site.register(Job, JobAdmin)


class AlertAdmin(admin.ModelAdmin):

    list_display        = ('id', 'job', 'message', 'details')
    list_filter         = ['job', 'message']
    search_fields       = ['job', 'message', 'details']
    list_display_links  = ('id',)

admin.site.register(Alert, AlertAdmin)

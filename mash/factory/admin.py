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


from mash.factory.models import *
from django.contrib import admin

class FactoryTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'config', 'taskNumber', 'description', 'imageName')

admin.site.register(FactoryTask, FactoryTaskAdmin)


class FactoryTaskResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'experiment', 'obsolete')
    list_filter  = ['obsolete']

admin.site.register(FactoryTaskResult, FactoryTaskResultAdmin)


class DebuggingEntryAdmin(admin.ModelAdmin):
    list_display        = ('id', 'task', 'sequence', 'start_frame', 'end_frame',
                           'heuristic_version', 'status', 'error_details', 'filename', 'obsolete')
    list_filter         = ['status', 'task', 'obsolete']
    list_display_links  = ('id', 'task', 'heuristic_version')

admin.site.register(DebuggingEntry, DebuggingEntryAdmin)

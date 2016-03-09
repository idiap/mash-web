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


from contests.models import *
from django.contrib import admin


class ContestAdmin(admin.ModelAdmin):

    list_display        = ('id', 'name', 'summary', 'configuration', 'reference_experiment', 'start', 'end', 'post')
    search_fields       = ['name', 'summary', 'description', 'configuration__name', 'reference_experiment__name']
    list_display_links  = ('id', 'name',)

admin.site.register(Contest, ContestAdmin)


class ContestEntryAdmin(admin.ModelAdmin):

    list_display        = ('id', 'contest', 'heuristic_version', 'experiment', 'rank')
    search_fields       = ['contest__name', 'heuristic_version__heuristic__author__username',
                           'heuristic_version__heuristic__name', 'experiment__name']
    list_display_links  = ('id',)

admin.site.register(ContestEntry, ContestEntryAdmin)

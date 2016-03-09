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


from mash.tasks.models import *
from django.contrib import admin


class TaskAdmin(admin.ModelAdmin):

    list_display        = ('name', 'description', 'type')
    list_filter         = ['type']
    search_fields       = ['name', 'description']
    list_display_links  = ('name',)
    ordering            = ('name', 'type')


class DatabaseAdmin(admin.ModelAdmin):

    list_display        = ('name', 'url', 'doc_url', 'description', 'has_standard_sets', 'task')
    search_fields       = ['name', 'description', 'has_standard_sets', 'task']
    list_display_links  = ('name',)
    ordering            = ('name', 'has_standard_sets', 'task')


class LabelAdmin(admin.ModelAdmin):

    list_display        = ('database', 'index', 'name')
    search_fields       = ['name', 'database__name']
    list_display_links  = ('index', 'name',)


class GoalAdmin(admin.ModelAdmin):

    list_display        = ('name', 'description', 'task')
    search_fields       = ['name', 'description', 'task']
    list_display_links  = ('name',)
    ordering            = ('name', 'task')


class EnvironmentAdmin(admin.ModelAdmin):

    list_display        = ('name', 'description')
    search_fields       = ['name', 'description']
    list_display_links  = ('name',)
    ordering            = ('name',)


admin.site.register(Task, TaskAdmin)
admin.site.register(Database, DatabaseAdmin)
admin.site.register(Label, LabelAdmin)
admin.site.register(Goal, GoalAdmin)
admin.site.register(Environment, EnvironmentAdmin)

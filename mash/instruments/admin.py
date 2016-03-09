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


from instruments.models import *
from django.contrib import admin


class InstrumentAdmin(admin.ModelAdmin):

    list_display        = ('id', 'author', 'name', 'description', 'status')
    list_filter         = ['author']
    search_fields       = ['author', 'name', 'description']
    list_display_links  = ('id', 'name',)
    ordering            = ('id', 'author', 'name',)


class DataReportAdmin(admin.ModelAdmin):

    list_display        = ('id', 'experiment', 'filename')
    search_fields       = ['experiment__name', 'experiment__user__username', 'filename']
    list_display_links  = ('id', 'filename',)
    ordering            = ('id', 'experiment', 'filename')


class ViewAdmin(admin.ModelAdmin):

    list_display        = ('id', 'instrument', 'name', 'title', 'used_in_experiment_results', 'used_in_factory_results', 'index')
    list_filter         = ['instrument', 'used_in_experiment_results', 'used_in_factory_results']
    search_fields       = ['instrument', 'name', 'title']
    list_display_links  = ('id', 'name',)
    ordering            = ('id', 'instrument', 'name', 'used_in_experiment_results', 'used_in_factory_results')


class ViewFileAdmin(admin.ModelAdmin):

    list_display        = ('id', 'view', 'type', 'filename', 'static', 'require')
    list_filter         = ['view', 'type', 'static']
    search_fields       = ['view', 'filename']
    list_display_links  = ('id', 'filename',)
    ordering            = ('id', 'view', 'type', 'filename', 'static')


class SnippetAdmin(admin.ModelAdmin):

    list_display        = ('id', 'report', 'view', 'status', 'folder')
    list_filter         = ['view']
    search_fields       = ['report', 'view', 'status', 'folder']
    list_display_links  = ('id', 'folder',)
    ordering            = ('id', 'report', 'view', 'folder', 'status',)


admin.site.register(Instrument, InstrumentAdmin)
admin.site.register(DataReport, DataReportAdmin)
admin.site.register(View, ViewAdmin)
admin.site.register(ViewFile, ViewFileAdmin)
admin.site.register(Snippet, SnippetAdmin)

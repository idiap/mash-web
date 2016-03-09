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


from mash.experiments.models import *
from django.contrib import admin


class ExperimentAdmin(admin.ModelAdmin):

    list_display        = ('id', 'name', 'configuration', 'user', 'status', 'creation_date', 'start', 'end')
    list_filter         = ['status']
    search_fields       = ['name', 'configuration__name', 'user__username']
    list_display_links  = ('name',)

admin.site.register(Experiment, ExperimentAdmin)


class ConfigurationAdmin(admin.ModelAdmin):

    list_display        = ('id', 'name', 'heuristics', 'experiment_type', 'task')
    list_filter         = ['heuristics', 'experiment_type', 'task']
    search_fields       = ['name']
    list_display_links  = ('name',)

admin.site.register(Configuration, ConfigurationAdmin)


class SettingAdmin(admin.ModelAdmin):

    list_display        = ('id', 'configuration', 'name', 'value')
    list_filter         = ['name']
    search_fields       = ['configuration__name', 'name', 'value']
    list_display_links  = ('id', 'name')
    list_editable       = ('value',)

admin.site.register(Setting, SettingAdmin)


class NotificationAdmin(admin.ModelAdmin):

    list_display        = ('id', 'experiment', 'name', 'value')
    list_filter         = ['name']
    search_fields       = ['experiment__name', 'name', 'value']
    list_display_links  = ('id', 'name',)
    list_editable       = ('value',)

admin.site.register(Notification, NotificationAdmin)


class ClassificationResultsAdmin(admin.ModelAdmin):

    list_display        = ('id', 'experiment', 'train_error', 'test_error')
    search_fields       = ['experiment__name']
    list_display_links  = ('id',)

admin.site.register(ClassificationResults, ClassificationResultsAdmin)


class GoalPlanningResultAdmin(admin.ModelAdmin):

    list_display        = ('id', 'experiment', 'nbGoalsReached', 'nbTasksFailed', 'nbActionsDone', 'nbMimickingErrors', 'nbNotRecommendedActions')
    list_filter         = ['experiment']
    search_fields       = ['experiment__name']
    list_display_links  = ('id',)

admin.site.register(GoalPlanningResult, GoalPlanningResultAdmin)

class GoalPlanningRoundAdmin(admin.ModelAdmin):

    list_display        = ('id', 'summary', 'round', 'result', 'score', 'nbActionsDone', 'nbMimickingErrors', 'nbNotRecommendedActions')
    list_filter         = ['round', 'result']
    search_fields       = ['summary__experiment__name']
    list_display_links  = ('id',)

admin.site.register(GoalPlanningRound, GoalPlanningRoundAdmin)

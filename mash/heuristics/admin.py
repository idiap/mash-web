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


from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.models import HeuristicEvaluationResults
from mash.heuristics.models import HeuristicEvaluationStep
from mash.heuristics.models import HeuristicSignature
from django.contrib import admin



class HeuristicAdmin(admin.ModelAdmin):

    list_display        = ('id', 'author', 'name', 'short_description',
                           'latest_public_version', 'latest_private_version', 'simple')
    list_filter         = ['simple']
    search_fields       = ['author__username', 'name', 'short_description']
    list_display_links  = ('id', 'name')

admin.site.register(Heuristic, HeuristicAdmin)


class HeuristicVersionAdmin(admin.ModelAdmin):
    
    def heuristic__short_description(self, obj):
        return obj.short_description
    
    list_display        = ('id', 'heuristic', 'version',
                           'heuristic__short_description', 'filename', 'upload_date',
                           'publication_date', 'opensource_date', 'status_date',
                           'checked', 'evaluated', 'public', 'status', 'rank')
    list_filter         = ['checked', 'evaluated', 'public', 'status']
    search_fields       = ['heuristic__author__username', 'heuristic__name',
                           'heuristic__short_description', 'filename']
    list_display_links  = ('id', 'heuristic', 'version')

admin.site.register(HeuristicVersion, HeuristicVersionAdmin)


class HeuristicTestStatusAdmin(admin.ModelAdmin):

    list_display        = ('id', 'heuristic_version', 'phase', 'error', 'details')
    list_filter         = ['phase']
    search_fields       = ['heuristic_version__absolutename', 'error', 'details']
    list_display_links  = ('id', 'heuristic_version')

admin.site.register(HeuristicTestStatus, HeuristicTestStatusAdmin)


class HeuristicEvaluationResultsAdmin(admin.ModelAdmin):

    list_display        = ('id', 'heuristic_version', 'evaluation_config', 'experiment', 'rank')
    search_fields       = ['heuristic_version__absolutename', 'configuration__name', 'experiment_name']
    list_display_links  = ('id', 'heuristic_version')

admin.site.register(HeuristicEvaluationResults, HeuristicEvaluationResultsAdmin)


class HeuristicEvaluationStepAdmin(admin.ModelAdmin):

    def heuristic_version(self, obj):
        return obj.evaluation_results.heuristic_version.absolutename()

    list_display        = ('id', 'heuristic_version', 'seed', 'train_error', 'test_error')
    search_fields       = ['evaluation_results__heuristic_version__absolutename']
    list_display_links  = ('id',)

admin.site.register(HeuristicEvaluationStep, HeuristicEvaluationStepAdmin)


class HeuristicSignatureAdmin(admin.ModelAdmin):

    list_display        = ('id', 'heuristic_version', 'experiment')
    search_fields       = ['heuristic_version__absolutename', 'experiment__name']
    list_display_links  = ('id', 'heuristic_version')

admin.site.register(HeuristicSignature, HeuristicSignatureAdmin)

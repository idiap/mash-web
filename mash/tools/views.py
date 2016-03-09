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


from mash.tools.models import PluginErrorReport
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.http import Http404


#---------------------------------------------------------------------------------------------------
# Display an error report
#---------------------------------------------------------------------------------------------------
def error_report(request, report_id):

    # Initialisations
    report          = None
    title_link      = None
    title_class     = 'red'
    experiment_text = None
    experiment_link = None
    experiment_name = None

    # Retrieve the report
    report = get_object_or_404(PluginErrorReport, pk=report_id)
    
    # Check that the user has the right to see the report
    if report.heuristic_version is not None:
        public_only = (request.user != report.heuristic_version.heuristic.author) and not(request.user.is_superuser)
        if public_only and not(report.heuristic_version.public):
            raise Http404
        title_link = '/heuristics/v%d/' % report.heuristic_version.id
    elif not(request.user.get_profile().project_member):
        raise Http404

    if (report.classifier is not None) or (report.goalplanner is not None) or (report.instrument is not None):
        title_class = 'green'

    (experiment_text, experiment_link, experiment_name) = _getExperimentInfos(report, request.user)

    # Rendering
    return render_to_response('tools/error_report.html',
                              {'report': report,
                               'display_title': True,
                               'title_class': title_class,
                               'title_link': title_link,
                               'experiment_text': experiment_text,
                               'experiment_link': experiment_link,
                               'experiment_name': experiment_name,
                              },
                              context_instance=RequestContext(request))


def get_error_report_as_html(report, user, display_title=False, title_class='red', title_link=None, display_experiment=False):

    # Initialisations
    experiment_text = None
    experiment_link = None
    experiment_name = None

    if display_experiment:
        (experiment_text, experiment_link, experiment_name) = _getExperimentInfos(report, user)

    context = {'report': report,
               'display_title': display_title,
               'title_class': title_class,
               'title_link': title_link,
               'experiment_text': experiment_text,
               'experiment_link': experiment_link,
               'experiment_name': experiment_name,
              }
    
    return loader.render_to_string('tools/embedded_error_report.html', context)


def _getExperimentInfos(report, user):

    # Initialisations
    experiment_text = None
    experiment_link = None
    experiment_name = None

    if report.experiment is not None:
        if report.experiment.isPublic():
            experiment_link = '/experiments/%d/' % report.experiment.id
            experiment_name = report.experiment.fullname()
        elif report.experiment.isConsortium():
            if not(user.is_anonymous()) and (user.get_profile() is not None) and user.get_profile().project_member:
                experiment_link = '/experiments/%d/' % report.experiment.id
                experiment_name = report.experiment.fullname()
            else:
                experiment_text = 'This error happened during an experiment scheduled by the consortium'
        elif report.experiment.isPrivate():
            if (user == report.experiment.user) or user.is_superuser:
                experiment_link = '/experiments/%d/' % report.experiment.id
                experiment_name = report.experiment.fullname()
            else:
                experiment_text = 'This error happened during a private experiment'
    
    return (experiment_text, experiment_link, experiment_name)

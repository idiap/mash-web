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


from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from contests.models import Contest, ContestEntry
from contests.utilities import ListConfiguration, ListRenderer, HeaderEntry, Constants
from contests.forms import EnterContestForm
from mash.tasks.models import Task, Database, Label, Goal, Environment
from mash.heuristics.models import HeuristicVersion
from mash.experiments.views import schedule_experiment
from mash.experiments.models import Configuration
from phpbb.utilities import createTopic
import utils.mediawiki as mediawiki


#---------------------------------------------------------------------------------------------------
# Create an entry for a heuristic version in a context
#---------------------------------------------------------------------------------------------------
def enter_contest(contest, heuristic_version):
    
    # Determine if the heuristic is already part of the model
    heuristic_versions = []
    additional_heuristics = []
    if contest.configuration.heuristics_set.filter(id=heuristic_version.id).count() > 0:
        additional_heuristics = [ heuristic_version ]
    else:
        heuristic_versions = [ heuristic_version ]
    
    # Schedule the experiment
    experiment = schedule_experiment(contest.configuration, Configuration.CONTEST_ENTRY,
                                     contest.name + '/' + heuristic_version.fullname(),
                                     contest.name + '/' + heuristic_version.fullname(),
                                     contest.configuration.heuristics, heuristic_versions,
                                     additional_heuristics, [],
                                     contest.configuration.predictorName())
    
    # Create the contest entry
    entry = ContestEntry()
    entry.contest             = contest
    entry.heuristic_version   = heuristic_version
    entry.experiment          = experiment
    entry.rank                = None
    entry.save()

    return entry


#---------------------------------------------------------------------------------------------------
# Display the lists of all the contests
#---------------------------------------------------------------------------------------------------
def contests_list(request):

    # Current contests
    configuration = ListConfiguration(request, Constants.CONTEST_TYPE_IN_PROGRESS)
    configuration.addHeaderEntry(HeaderEntry('NAME',        Constants.SORT_KEY_NAME))
    configuration.addHeaderEntry(HeaderEntry('DESCRIPTION'))
    configuration.addHeaderEntry(HeaderEntry('# ENTRIES',   Constants.SORT_KEY_NB_ENTRIES))
    configuration.addHeaderEntry(HeaderEntry('BEST ENTRY',  Constants.SORT_KEY_BEST_ENTRY))
    configuration.addHeaderEntry(HeaderEntry('BEST RESULT'))
    configuration.addHeaderEntry(HeaderEntry('START DATE',  Constants.SORT_KEY_START_DATE))
    configuration.addHeaderEntry(HeaderEntry('END DATE',    Constants.SORT_KEY_END_DATE))

    current_contests_html = ListRenderer(configuration).render()

    # Future contests
    configuration = ListConfiguration(request, Constants.CONTEST_TYPE_FUTURE)
    configuration.addHeaderEntry(HeaderEntry('NAME',        Constants.SORT_KEY_NAME))
    configuration.addHeaderEntry(HeaderEntry('DESCRIPTION'))
    configuration.addHeaderEntry(HeaderEntry('START DATE',  Constants.SORT_KEY_START_DATE))
    configuration.addHeaderEntry(HeaderEntry('END DATE',    Constants.SORT_KEY_END_DATE))

    future_contests_html = ListRenderer(configuration).render()

    # Finished contests
    configuration = ListConfiguration(request, Constants.CONTEST_TYPE_FINISHED)
    configuration.addHeaderEntry(HeaderEntry('NAME',        Constants.SORT_KEY_NAME))
    configuration.addHeaderEntry(HeaderEntry('DESCRIPTION'))
    configuration.addHeaderEntry(HeaderEntry('# ENTRIES',   Constants.SORT_KEY_NB_ENTRIES))
    configuration.addHeaderEntry(HeaderEntry('BEST ENTRY',  Constants.SORT_KEY_BEST_ENTRY))
    configuration.addHeaderEntry(HeaderEntry('BEST RESULT'))
    configuration.addHeaderEntry(HeaderEntry('START DATE',  Constants.SORT_KEY_START_DATE))
    configuration.addHeaderEntry(HeaderEntry('END DATE',    Constants.SORT_KEY_END_DATE))

    finished_contests_html = ListRenderer(configuration).render()

    # Rendering
    return render_to_response('contests/list.html',
                              {'current_contests_html': current_contests_html,
                               'future_contests_html': future_contests_html,
                               'finished_contests_html': finished_contests_html,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display a contest
#---------------------------------------------------------------------------------------------------
def contest(request, contest_id):
    
    # Retrieve the contest
    contest = get_object_or_404(Contest, pk=contest_id)

    # Process the form, if any
    form = None
    if (request.method == 'POST') and request.POST.has_key('submit'):
        form = EnterContestForm(request.POST)
        if form.is_valid() and (request.POST['submit'] == 'Enter the contest'):
            versions = HeuristicVersion.objects.filter(id__in=form.cleaned_data['heuristic_versions'].split(' '))
            
            if len(versions) == 1:
                entry = enter_contest(contest, versions[0])
                return HttpResponseRedirect('/experiments/%d/' % entry.experiment.id)
            else:
                for version in versions:
                    enter_contest(contest, version)
                return HttpResponseRedirect('/contests/%d/' % contest.id)


    # Parse the mediawiki-style context description
    if len(contest.description.strip()) > 0:
        description = contest.description.strip()
        
        if contest.reference_experiment is not None:
            description = description.replace('$REFERENCE_EXPERIMENT',
                                              '[/experiments/%d/ %s]' % (contest.reference_experiment.id, contest.reference_experiment.name))
        else:
            description = description.replace('$REFERENCE_EXPERIMENT', 'UNKNOWN')

        description = mediawiki.parse(description, showToc=False)
    else:
        description = None

    # Generate the content of the 'database box' (if necessary)
    database_box_content = None
    if (contest.configuration.task.type == Task.TYPE_CLASSIFICATION) or (contest.configuration.task.type == Task.TYPE_OBJECT_DETECTION):
        db_name = contest.configuration.databaseName()
        training_ratio = contest.configuration.trainingRatio()
        label_indices = contest.configuration.labels()

        database_box_content = '<dl>\n' \
                               '    <dt>Name:</dt>\n' \
                               '    <dd>' + db_name + '</dd>\n' \
                               '    <dt>Training ratio:</dt>\n'

        if training_ratio is not None:
            database_box_content += '    <dd>' + str(float(training_ratio) * 100) + '%</dd>\n'
        else:
            database_box_content += '    <dd>Defined by the database</dd>\n'

        database_box_content += '    <dt>Used labels:</dt>\n'

        database = get_object_or_404(Database, name=db_name)
        if (label_indices is None) or (len(label_indices) == database.labels.count()):
            if database.labels.count() > 1:
                database_box_content += '    <dd>All (%d labels)</dd>\n' % database.labels.count()
            else:
                database_box_content += '    <dd>All (1 label)</dd>\n'
        else:
            database_box_content += '    <dd>%d/%d</dd>\n' % (len(label_indices), database.labels.count())
            database_box_content += '    <dd><ul class="labels_list">\n'
            labels = database.labels.filter(index__in=label_indices).order_by('name')
            for label in labels:
                database_box_content += '        <li>%s</li>\n' % label.name
            database_box_content += '    </ul></dd>\n'

        database_box_content += '</dl>\n'

    # Generate the content of the 'goal-planning task box' (if necessary)
    goalplanning_task_box_content = None
    if contest.configuration.task.type == Task.TYPE_GOALPLANNING:
        goal_name = contest.configuration.goalName()
        environment_name = contest.configuration.environmentName()

        goalplanning_task_box_content = '<dl>\n' \
                                        '    <dt>Type:</dt>\n' \
                                        '    <dd>' + contest.configuration.task.name + '</dd>\n' \
                                        '    <dt>Goal:</dt>\n' \
                                        '    <dd>' + goal_name + '</dd>\n' \
                                        '    <dt>Environment:</dt>\n' \
                                        '    <dd>' + environment_name + '</dd>\n' \
                                        '</dl>\n'

    # Generate the content of the 'predictor box'
    predictor_box_content = '<dl>\n'

    predictor_name = contest.configuration.predictorName()
    if predictor_name is not None:
        predictor_box_content += '    <dt>Name:</dt>\n' \
                                 '    <dd>%s</dd>\n' % predictor_name

    predictor_box_content += '</dl>\n'

    # Generate the content of the 'heuristics box'
    heuristics_box_content = None
    if contest.configuration.heuristics_set.count() > 0:
        heuristics_box_content = '<ul>\n'
        heuristics_list = contest.configuration.heuristics_set.all().order_by('heuristic__author__username', 'heuristic__name', 'version')
        for heuristic in heuristics_list:
            if heuristic.status == HeuristicVersion.STATUS_DISABLED:
                heuristics_box_content += '<li><a href="/heuristics/v%d" class="disabled" title="The heuristic \'%s\' has been disabled, due to an error">%s</a></li>\n' % (heuristic.id, heuristic.fullname(), heuristic.fullname())
            elif heuristic.status == HeuristicVersion.STATUS_DELETED:
                heuristics_box_content += '<li><span class="deleted" title="The heuristic \'%s\' has been deleted">%s</span></li>\n' % (heuristic.fullname(), heuristic.fullname())
            else:
                heuristics_box_content += '<li><a href="/heuristics/v%d">%s</a></li>\n' % (heuristic.id, heuristic.fullname())

        heuristics_box_content += '</ul>\n'

    # Generate the content of the 'results box'
    results_box_content = None
    improvement_reference = None
    if contest.reference_experiment is not None:
        if (contest.configuration.task.type == Task.TYPE_CLASSIFICATION) or (contest.configuration.task.type == Task.TYPE_OBJECT_DETECTION):
            try:
                results = contest.reference_experiment.classification_results
            except:
                results = None

            results_box_content = '<dl>\n' \
                                  '    <dt>Experiment:</dt>\n' \
                                  '    <dd><a href="/experiments/%d/">%s</a></dd>\n' \
                                  '    <dt>Training error:</dt>\n' % (contest.reference_experiment.id, contest.reference_experiment.name)

            if (results is not None) and (results.train_error is not None):
                results_box_content += '    <dd>%s</dd>\n' % results.displayableTrainError()
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '    <dt>Test error:</dt>\n'

            if (results is not None) and (results.test_error is not None):
                results_box_content += '    <dd>%s</dd>\n' % results.displayableTestError()
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '</dl>\n'

            improvement_reference = str(contest.reference_experiment.classification_results.test_error)

        elif contest.configuration.task.type == Task.TYPE_GOALPLANNING:
            try:
                results = contest.reference_experiment.goalplanning_results
            except:
                results = None

            results_box_content = '<dl>\n' \
                                  '    <dt>Training result:</dt>\n'

            if results is not None:
                r = results.filter(training=True)
                if r.count() > 0:
                    results_box_content += '    <dd>%s</dd>\n' % r[0].result_text()
                else:
                    results_box_content += '    <dd>-</dd>\n'
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '    <dt>Successful tests:</dt>\n'

            if results.count() > 0:
                r = results.filter(training=False, result=GoalPlanningResult.RESULT_GOAL_REACHED)
                if r.count() > 0:
                    mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                    best = reduce(lambda x, y: max(x, y.score), r, 0)
                    low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                    results_box_content += '    <dd>%d (mean score: %f, best score: %f, lowest score: %f)</dd>\n' % (r.count(), mean, best, low)
                else:
                    results_box_content += '    <dd>0</dd>\n'
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '    <dt>Unsuccessful tests:</dt>\n'

            if results.count() > 0:
                r = results.filter(training=False, result=GoalPlanningResult.RESULT_NONE)
                if r.count() > 0:
                    mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                    best = reduce(lambda x, y: max(x, y.score), r, 0)
                    low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                    results_box_content += '    <dd>%d (mean score: %f, best score: %f, lowest score: %f)</dd>\n' % (r.count(), mean, best, low)
                else:
                    results_box_content += '    <dd>0</dd>\n'
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '    <dt>Failed tests:</dt>\n'

            if results.count() > 0:
                r = results.filter(training=False, result=GoalPlanningResult.RESULT_TASK_FAILED)
                if r.count() > 0:
                    mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                    best = reduce(lambda x, y: max(x, y.score), r, 0)
                    low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                    results_box_content += '    <dd>%d (mean score: %f, best score: %f, lowest score: %f)</dd>\n' % (r.count(), mean, best, low)
                else:
                    results_box_content += '    <dd>0</dd>\n'
            else:
                results_box_content += '    <dd>-</dd>\n'

            results_box_content += '</dl>\n'

    # Contributors entries
    configuration = ListConfiguration(request, Constants.CONTEST_CONTRIBUTORS_ENTRIES, contest=contest)
    configuration.addHeaderEntry(HeaderEntry('RANK',            Constants.SORT_KEY_RANK))

    if improvement_reference is not None:
        configuration.addHeaderEntry(HeaderEntry('DELTA'))

    configuration.addHeaderEntry(HeaderEntry('HEURISTIC',       Constants.SORT_KEY_HEURISTIC))
    configuration.addHeaderEntry(HeaderEntry('DESCRIPTION'))
    configuration.addHeaderEntry(HeaderEntry('EXPERIMENT',      Constants.SORT_KEY_EXPERIMENT))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('JOIN DATE',       Constants.SORT_KEY_JOIN_DATE))

    configuration.improvement_reference = improvement_reference

    contributors_entries_html = ListRenderer(configuration).render()

    # Consortium entries
    configuration = ListConfiguration(request, Constants.CONTEST_CONSORTIUM_ENTRIES, contest=contest)
    configuration.addHeaderEntry(HeaderEntry('RANK',            Constants.SORT_KEY_RANK))

    if improvement_reference is not None:
        configuration.addHeaderEntry(HeaderEntry('DELTA'))

    configuration.addHeaderEntry(HeaderEntry('HEURISTIC',       Constants.SORT_KEY_HEURISTIC))
    configuration.addHeaderEntry(HeaderEntry('DESCRIPTION'))
    configuration.addHeaderEntry(HeaderEntry('EXPERIMENT',      Constants.SORT_KEY_EXPERIMENT))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('JOIN DATE',       Constants.SORT_KEY_JOIN_DATE))

    configuration.improvement_reference = improvement_reference

    consortium_entries_html = ListRenderer(configuration).render()

    # Retrieve the list of heuristics that can enter the competition
    usable_heuristic_versions = None
    nb_private_heuristics = 0
    if not(request.user.is_anonymous()) and contest.isInProgress():
        unusable_heuristic_versions = map(lambda x: x.heuristic_version.id, contest.entries.all())
        unusable_heuristic_versions.extend(map(lambda x: x.id, contest.configuration.heuristics_set.all()))
        usable_heuristic_versions = map(lambda x: x.latest_public_version, request.user.heuristics.filter(latest_public_version__isnull=False).exclude(latest_public_version__in=unusable_heuristic_versions))
        nb_private_heuristics = request.user.heuristics.filter(latest_public_version__isnull=True,
                                                               latest_private_version__status=HeuristicVersion.STATUS_OK,
                                                               latest_private_version__evaluated=True).count()

        if form is None:
            data = {
                'heuristic_versions': '-1',
            }

            form = EnterContestForm(data)

    # Rendering
    return render_to_response('contests/contest.html',
                              {'contest': contest,
                               'description': description,
                               'database_box_content': database_box_content,
                               'goalplanning_task_box_content': goalplanning_task_box_content,
                               'predictor_box_content': predictor_box_content,
                               'heuristics_box_content': heuristics_box_content,
                               'results_box_content': results_box_content,
                               'usable_heuristic_versions': usable_heuristic_versions,
                               'nb_private_heuristics': nb_private_heuristics,
                               'form': form,
                               'contributors_entries_html': contributors_entries_html,
                               'consortium_entries_html': consortium_entries_html,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Handle the creation of/redirection to the official forum topic of a contest
#---------------------------------------------------------------------------------------------------
def topic(request, contest_id):

    # Retrieve the contest
    contest = get_object_or_404(Contest, pk=contest_id)

    # Create the contest topic if it don't already exists
    if contest.post is None:
        createTopic(contest, 'Contests', contest.name,
                    'contests/%d/' % contest.id, 'contest')

    # Go to the topic
    return HttpResponseRedirect('/forum/viewtopic.php?t=%d' % contest.post.topic.topic_id)



#---------------------------------------------------------------------------------------------------
# Super-user only: Create an entry in a contest for a heuristic version
#---------------------------------------------------------------------------------------------------
def enter(request, contest_id, heuristic_version_id):

    if not(request.user.is_superuser):
        raise Http404

    # Retrieve the contest
    contest = get_object_or_404(Contest, pk=contest_id)

    # Retrieve the heuristic version
    heuristic_version = get_object_or_404(HeuristicVersion, pk=heuristic_version_id)

    # Enter the contest
    entry = enter_contest(contest, heuristic_version)
    return HttpResponseRedirect('/experiments/%d/' % entry.experiment.id)

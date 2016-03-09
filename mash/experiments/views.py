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


from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.models import User
from mash.experiments.models import Experiment, Configuration, Setting, GoalPlanningResult, GoalPlanningRound
from mash.experiments.forms import NewImageBasedExperimentForm, NewGoalplanningExperimentForm
from mash.experiments.utilities import ListConfiguration, ListRenderer, HeaderEntry
from mash.heuristics.models import Heuristic, HeuristicVersion
from classifiers.models import Classifier
from goalplanners.models import Goalplanner
from instruments.views import get_snippets
from tools.models import PluginErrorReport
from tools.views import get_error_report_as_html
from mash.servers.models import Job
from texts_db.models import Text
from mash.tasks.models import Task, Database, Label, Goal, Environment
from servers import acquireExperimentsScheduler, releaseExperimentsScheduler
from phpbb.utilities import createTopic
from pymash.messages import Message
import datetime


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

MAX_NB_PUBLIC_HEURISTICS_IN_PRIVATE_EXPERIMENTS = 3


####################################################################################################
#
# UTILITY FUNCTIONS
#
####################################################################################################

def schedule_experiment(template_configuration, experiment_type,
                        experiment_name, configuration_name,
                        heuristics_type, heuristic_versions,
                        additional_heuristic_versions,
                        settings, predictor, user=None):
    
    # Create the configuration in the database
    configuration                   = Configuration()
    configuration.name              = configuration_name
    configuration.experiment_type   = experiment_type
    configuration.heuristics        = heuristics_type
    configuration.task              = template_configuration.task
    configuration.save()
    
    # Add the list of heuristic versions
    for version in template_configuration.heuristics_set.all():
        configuration.heuristics_set.add(version)

    for version in heuristic_versions:
        configuration.heuristics_set.add(version)

    for version in additional_heuristic_versions:
        configuration.heuristics_set.add(version)
    
    # Add the list of instruments
    for instrument in template_configuration.instruments_set.all():
        configuration.instruments_set.add(instrument)

    # Save the configuration 
    configuration.save()
    
    # Add the settings
    for setting in template_configuration.settings.all():
        configuration.addSetting(setting.name, setting.value)
    
    for setting in settings:
        if len(setting) == 2:
            configuration.addSetting(setting[0], setting[1])
        else:
            configuration.addSetting(setting[0], setting[1], section=setting[2])
    
    if isinstance(predictor, str) or isinstance(predictor, unicode):
        configuration.addSetting('USE_PREDICTOR', predictor)
    else:
        configuration.addSetting('USE_PREDICTOR', predictor.fullname())
    
    if len(additional_heuristic_versions) > 0:
        configuration.addSetting('PREDICTOR_SETUP/ADDITIONAL_HEURISTICS', ' '.join(map(lambda x: x.absolutename(), additional_heuristic_versions)))
    
    # Create the experiment in the database
    experiment                  = Experiment()
    experiment.name             = experiment_name
    experiment.configuration    = configuration
    experiment.user             = user
    experiment.save()
    
    # Tell the Experiments Scheduler about the new experiment
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand(Message('RUN_EXPERIMENT', [experiment.id]))
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)
    
    return experiment


####################################################################################################
#
# VIEWS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Display the results of an experiment
#---------------------------------------------------------------------------------------------------
def experiment(request, experiment_id):

    # Retrieve the experiment
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    
    # Check that the user can see this experiment
    if (experiment.configuration.experiment_type != Configuration.PUBLIC) and \
       (experiment.configuration.experiment_type != Configuration.CONTEST_BASE) and \
       (experiment.configuration.experiment_type != Configuration.CONTEST_ENTRY) and \
       not(request.user.is_superuser):
        if request.user.is_anonymous():
            raise Http404
        if (experiment.configuration.experiment_type == Configuration.PRIVATE) and (request.user != experiment.user):
            raise Http404
        if (experiment.configuration.experiment_type == Configuration.CONSORTIUM) and not(request.user.get_profile().project_member):
            raise Http404

    if experiment.isDeleted() and not(request.user.is_superuser):
        raise Http404
    
    # Generate the content of the 'database box' (if necessary)
    database_box_content = None
    if (experiment.configuration.task.type == Task.TYPE_CLASSIFICATION) or (experiment.configuration.task.type == Task.TYPE_OBJECT_DETECTION):
        db_name = experiment.configuration.databaseName()
        training_ratio = experiment.configuration.trainingRatio()
        label_indices = experiment.configuration.labels()
    
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
    if experiment.configuration.task.type == Task.TYPE_GOALPLANNING:
        goal_name = experiment.configuration.goalName()
        environment_name = experiment.configuration.environmentName()

        goalplanning_task_box_content = '<dl>\n' \
                                        '    <dt>Type:</dt>\n' \
                                        '    <dd>' + experiment.configuration.task.name + '</dd>\n' \
                                        '    <dt>Goal:</dt>\n' \
                                        '    <dd>' + goal_name + '</dd>\n' \
                                        '    <dt>Environment:</dt>\n' \
                                        '    <dd>' + environment_name + '</dd>\n' \
                                        '</dl>\n'
    
    # Generate the content of the 'predictor box'
    predictor_box_content = '<dl>\n'

    predictor_name = experiment.configuration.predictorName()
    if predictor_name is not None:
        predictor_box_content += '    <dt>Name:</dt>\n' \
                                 '    <dd>%s</dd>\n' % predictor_name
                             
    if experiment.configuration.experiment_type == Configuration.CONSORTIUM:
        settings_list = experiment.configuration.settings.filter(name__startswith='PREDICTOR_SETUP/')
        if len(settings_list) > 0:
            predictor_box_content += '    <dt>Settings:</dt>\n'
            for setting in settings_list:
                predictor_box_content += '    <dd>' + setting.name[16:] + ' ' + setting.value + '</dd>\n'

    predictor_box_content += '</dl>\n'

    # Generate the content of the 'heuristics box'
    heuristics_box_content = '<ul>\n'
    heuristics_list = experiment.configuration.heuristics_set.all().order_by('heuristic__author__username', 'heuristic__name', 'version')
    for heuristic in heuristics_list:
        if heuristic.status == HeuristicVersion.STATUS_DISABLED:
            heuristics_box_content += '<li><a href="/heuristics/v%d" class="disabled" title="The heuristic \'%s\' has been disabled, due to an error">%s</a></li>\n' % (heuristic.id, heuristic.fullname(), heuristic.fullname())
        elif heuristic.status == HeuristicVersion.STATUS_DELETED:
            heuristics_box_content += '<li><span class="deleted" title="The heuristic \'%s\' has been deleted">%s</span></li>\n' % (heuristic.fullname(), heuristic.fullname())
        else:
            heuristics_box_content += '<li><a href="/heuristics/v%d">%s</a></li>\n' % (heuristic.id, heuristic.fullname())

    heuristics_box_content += '</ul>\n'

    # Generate the content of the 'results box'
    if (experiment.configuration.task.type == Task.TYPE_CLASSIFICATION) or (experiment.configuration.task.type == Task.TYPE_OBJECT_DETECTION):
        try:
            results = experiment.classification_results
        except:
            results = None
    
        results_box_content = '<dl>\n' \
                              '    <dt>Training error:</dt>\n'

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

    elif experiment.configuration.task.type == Task.TYPE_GOALPLANNING:
        try:
            results = experiment.goalplanning_results.all()[0]
        except:
            results = None

        results_box_content = '<dl>\n'

        if results is not None:
            nb_rounds_done = results.goalplanning_rounds.count()

            r = results.goalplanning_rounds.filter(result=GoalPlanningRound.RESULT_GOAL_REACHED)
            scores = ''
            if r.count() > 0:
                mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                best = reduce(lambda x, y: max(x, y.score), r, 0)
                low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                scores = ' (mean score: %f, best score: %f, lowest score: %f)' % (mean, best, low)

            results_box_content += '    <dt>Nb goals reached:</dt>\n<dd>%d / %d%s</dd>\n' % (results.nbGoalsReached, nb_rounds_done, scores)

            r = results.goalplanning_rounds.filter(result=GoalPlanningRound.RESULT_TASK_FAILED)
            scores = ''
            if r.count() > 0:
                mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                best = reduce(lambda x, y: max(x, y.score), r, 0)
                low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                scores = ' (mean score: %f, best score: %f, lowest score: %f)' % (mean, best, low)

            results_box_content += '    <dt>Nb tasks failed:</dt>\n<dd>%d / %d%s</dd>\n' % (results.nbTasksFailed, nb_rounds_done, scores)

            r = results.goalplanning_rounds.filter(result=GoalPlanningRound.RESULT_NONE)
            scores = ''
            if r.count() > 0:
                mean = reduce(lambda x, y: x + y.score, r, 0) / r.count()
                best = reduce(lambda x, y: max(x, y.score), r, 0)
                low = reduce(lambda x, y: min(x, y.score), r, r[0].score)
                scores = ' (mean score: %f, best score: %f, lowest score: %f)' % (mean, best, low)

            results_box_content += '    <dt>Nb unfinished rounds:</dt>\n<dd>%d / %d%s</dd>\n' % (nb_rounds_done - results.nbTasksFailed - results.nbGoalsReached, nb_rounds_done, scores)

            results_box_content += '    <dt>Nb actions done:</dt>\n<dd>%d</dd>\n' % results.nbActionsDone
        else:
            results_box_content += '    <dt>Nb goals reached:</dt>\n<dd>-</dd>\n'
            results_box_content += '    <dt>Nb tasks failed:</dt>\n<dd>-</dd>\n'
            results_box_content += '    <dt>Nb unfinished rounds:</dt>\n<dd>-</dd>\n'
            results_box_content += '    <dt>Nb actions done:</dt>\n<dd>-</dd>\n'

        results_box_content += '</dl>\n'

    # Retrieve the snippets of the instruments (if any)
    snippets = []
    snippets_css_files = []
    snippets_js_files = []
    try:
        for instrument in experiment.data_report.instruments_set.iterator():
            (report_snippets, report_snippets_css_files, report_snippets_js_files) = get_snippets(experiment.data_report, instrument, used_in_experiment_results=True)
            if report_snippets is None:
                continue
            
            snippets.extend(report_snippets)
            snippets_css_files.extend(filter(lambda x: x not in snippets_css_files, report_snippets_css_files))
            snippets_js_files.extend(filter(lambda x: x not in snippets_js_files, report_snippets_js_files))
    except:
        pass

    snippets.sort(lambda x, y: cmp(x.view.index, y.view.index))

    # Retrieve the error report of the predictor (if any)
    html_predictor_error_report = None
    try:
        error_report = PluginErrorReport.objects.filter(experiment=experiment, classifier__isnull=False).get()
        if not(request.user.is_anonymous()) and request.user.get_profile().project_member:
            html_predictor_error_report = get_error_report_as_html(error_report, request.user)
        else:
            html_predictor_error_report = "<p>%s</p>" % error_report.problemDescription()
    except:
        pass

    # Retrieve the list of heuristics that had problems
    problematic_heuristics = None
    try:
        error_reports = PluginErrorReport.objects.filter(experiment=experiment, heuristic_version__isnull=False)
        problematic_heuristics = map(lambda x: x.heuristic_version, error_reports)
    except:
        pass

    # Retrieve the list of instruments that had problems
    problematic_instruments = None
    if not(request.user.is_anonymous()) and request.user.get_profile().project_member:
        try:
            error_reports = PluginErrorReport.objects.filter(experiment=experiment, instrument__isnull=False)
            problematic_instruments = map(lambda x: x.instrument, error_reports)
        except:
            pass

    # Retrieve the list of log files
    log_files = None
    if not(request.user.is_anonymous()) and request.user.get_profile().project_member:
        try:
            job = Job.objects.filter(experiment=experiment).get()
            log_files = job.logs.files.all()
        except:
            pass

    # Retrieves the additional texts that might be needed
    text_cancellation_confirmation = Text.getContent('EXPERIMENT_CANCELLATION_CONFIRMATION')
    text_deletion_confirmation = Text.getContent('EXPERIMENT_DELETION_CONFIRMATION')

    # Rendering
    return render_to_response('experiments/experiment.html',
                              {'experiment': experiment,
                               'database_box_content': database_box_content,
                               'goalplanning_task_box_content': goalplanning_task_box_content,
                               'predictor_box_content': predictor_box_content,
                               'heuristics_box_content': heuristics_box_content,
                               'results_box_content': results_box_content,
                               'snippets': snippets,
                               'snippets_css_files': snippets_css_files,
                               'snippets_js_files': snippets_js_files,
                               'html_predictor_error_report': html_predictor_error_report,
                               'problematic_heuristics': problematic_heuristics,
                               'problematic_instruments': problematic_instruments,
                               'log_files': log_files,
                               'text_cancellation_confirmation': text_cancellation_confirmation,
                               'text_deletion_confirmation': text_deletion_confirmation,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display a list of the public experiments
#---------------------------------------------------------------------------------------------------
def public_experiments_list(request):

    # Setup the rendering
    configuration = ListConfiguration(request, Configuration.PUBLIC)
    configuration.addHeaderEntry(HeaderEntry('NAME', 'n'))
    configuration.addHeaderEntry(HeaderEntry('TASK', 't'))
    configuration.addHeaderEntry(HeaderEntry('DETAILS'))
    configuration.addHeaderEntry(HeaderEntry('PREDICTOR', 'p'))
    configuration.addHeaderEntry(HeaderEntry('# HEURISTICS', 'h'))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('CREATION DATE', 'c'))
    configuration.addHeaderEntry(HeaderEntry('START DATE', 's'))
    configuration.addHeaderEntry(HeaderEntry('DURATION', 'd'))
    
    # Rendering
    return ListRenderer(configuration).renderExperimentsList()


#---------------------------------------------------------------------------------------------------
# Display a list of the consortium experiments
#---------------------------------------------------------------------------------------------------
@login_required
def consortium_experiments_list(request):

    # Check that the user has the right to see that
    if not(request.user.get_profile().project_member):
        raise Http404           

    # Setup the rendering
    configuration = ListConfiguration(request, Configuration.CONSORTIUM)
    configuration.addHeaderEntry(HeaderEntry('USER', 'u'))
    configuration.addHeaderEntry(HeaderEntry('NAME', 'n'))
    configuration.addHeaderEntry(HeaderEntry('TASK', 't'))
    configuration.addHeaderEntry(HeaderEntry('DETAILS'))
    configuration.addHeaderEntry(HeaderEntry('PREDICTOR', 'p'))
    configuration.addHeaderEntry(HeaderEntry('# HEURISTICS', 'h'))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('CREATION DATE', 'c'))
    configuration.addHeaderEntry(HeaderEntry('START DATE', 's'))
    configuration.addHeaderEntry(HeaderEntry('DURATION', 'd'))

    # Rendering
    return ListRenderer(configuration).renderExperimentsList()


#---------------------------------------------------------------------------------------------------
# Display a list of the contest base experiments
#---------------------------------------------------------------------------------------------------
@login_required
def contest_experiments_list(request):

    # Check that the user has the right to see that
    if not(request.user.is_superuser):
        raise Http404           

    # Setup the rendering
    configuration = ListConfiguration(request, Configuration.CONTEST_BASE)
    configuration.addHeaderEntry(HeaderEntry('NAME', 'n'))
    configuration.addHeaderEntry(HeaderEntry('TASK', 't'))
    configuration.addHeaderEntry(HeaderEntry('DETAILS'))
    configuration.addHeaderEntry(HeaderEntry('PREDICTOR', 'p'))
    configuration.addHeaderEntry(HeaderEntry('# HEURISTICS', 'h'))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('CREATION DATE', 'c'))
    configuration.addHeaderEntry(HeaderEntry('START DATE', 's'))
    configuration.addHeaderEntry(HeaderEntry('DURATION', 'd'))

    # Rendering
    return ListRenderer(configuration).renderExperimentsList()


#---------------------------------------------------------------------------------------------------
# Display a list of the private experiments of a user
#---------------------------------------------------------------------------------------------------
@login_required
def private_experiments_list(request, user_id=None):

    user = None

    # Check that the user has the right to see that
    if user_id is not None:
        if (request.user.id != user_id) and not(request.user.is_superuser):
            raise Http404           
        user = User.objects.get(pk = user_id)
    else:
        user = request.user

    # Setup the rendering
    configuration = ListConfiguration(request, Configuration.PRIVATE, user)
    configuration.addHeaderEntry(HeaderEntry('NAME', 'n'))
    configuration.addHeaderEntry(HeaderEntry('TASK', 't'))
    configuration.addHeaderEntry(HeaderEntry('DETAILS'))
    configuration.addHeaderEntry(HeaderEntry('PREDICTOR', 'p'))
    configuration.addHeaderEntry(HeaderEntry('# HEURISTICS', 'h'))
    configuration.addHeaderEntry(HeaderEntry('RESULTS'))
    configuration.addHeaderEntry(HeaderEntry('CREATION DATE', 'c'))
    configuration.addHeaderEntry(HeaderEntry('START DATE', 's'))
    configuration.addHeaderEntry(HeaderEntry('DURATION', 'd'))
    
    # Rendering
    return ListRenderer(configuration).renderExperimentsList()


#---------------------------------------------------------------------------------------------------
# Used to schedule a private experiment
#---------------------------------------------------------------------------------------------------
@login_required
def experiments_schedule_private(request):

    # Retrieve the reference experiment (if any)
    reference_experiment = None
    if request.GET.has_key('ref'):
        try:
            reference_experiment = Experiment.objects.get(id=int(request.GET['ref']))
            if not(reference_experiment.isPrivate()):
                reference_experiment = None
        except:
            pass

    # Retrieve the type of task
    if reference_experiment is None:
        task_type = Task.TYPE_CLASSIFICATION
        if request.GET.has_key('t'):
            task_type = request.GET['t']
            if task_type not in [Task.TYPE_CLASSIFICATION, Task.TYPE_OBJECT_DETECTION, Task.TYPE_GOALPLANNING]:
                task_type = Task.TYPE_CLASSIFICATION
    else:
        task_type = reference_experiment.configuration.task.type

    # Process the form
    form = None
    if (request.method == 'POST') and request.POST.has_key('submit'):
    
        if request.POST['submit'] == 'Cancel':
            return HttpResponseRedirect('/experiments/private/')
        
        if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
            form = NewImageBasedExperimentForm(request.POST)
            form.detection = (task_type == Task.TYPE_OBJECT_DETECTION)

        elif task_type == Task.TYPE_GOALPLANNING:
            form = NewGoalplanningExperimentForm(request.POST)

        if form.is_valid() and (request.POST['submit'] == 'Schedule'):

            # Retrieve the list of heuristic versions to use
            heuristic_versions = HeuristicVersion.objects.filter(id__in=form.cleaned_data['heuristics'].split(' '))
            
            if len(filter(lambda x: x.heuristic.author != request.user, heuristic_versions)) > MAX_NB_PUBLIC_HEURISTICS_IN_PRIVATE_EXPERIMENTS:
                form.errors["heuristics"] = form.error_class([u"You can't select more than %d public heuristics" % MAX_NB_PUBLIC_HEURISTICS_IN_PRIVATE_EXPERIMENTS])

            else:
                if task_type == Task.TYPE_CLASSIFICATION:
                    template_name = 'classification'
                elif task_type == Task.TYPE_OBJECT_DETECTION:
                    template_name = 'detection'
                elif task_type == Task.TYPE_GOALPLANNING:
                    template_name = 'goalplanning'
    
                # Retrieve the configuration template
                if task_type == Task.TYPE_GOALPLANNING:
                    template = Configuration.objects.filter(name='template/%s' % template_name).filter(experiment_type=Configuration.PRIVATE, task=form.cleaned_data['task_type'])[0]
                else:
                    template = Configuration.objects.filter(name='template/%s' % template_name).filter(experiment_type=Configuration.PRIVATE)[0]

                # Retrieve the name, generate one if necessary
                experiment_name = form.cleaned_data['name']
                if len(experiment_name) == 0:
                    experiment_name = '%s/%d' % (template_name, Experiment.objects.filter(configuration__experiment_type=Configuration.PRIVATE,
                                                                                          user=request.user,
                                                                                          configuration__task__type=template.task.type).count() + 1)

                # Retrieve the settings and the predictor to use
                settings = []
                predictor = None
                
                if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
                    db = Database.objects.get(id=form.cleaned_data['database'])
                    settings.append( ('DATABASE_NAME', db.name, 'EXPERIMENT_SETUP') )
                    
                    if not(db.has_standard_sets) or not(form.cleaned_data['use_standard_sets']):
                        settings.append( ('TRAINING_SAMPLES', form.cleaned_data['training_ratio'], 'EXPERIMENT_SETUP') )
                    
                    settings.append( ('LABELS', form.cleaned_data['labels'], 'EXPERIMENT_SETUP') )
                    
                    predictor = Classifier.objects.get(id=form.cleaned_data['predictor'])
                
                elif task_type == Task.TYPE_GOALPLANNING:
                    goal = Goal.objects.get(id=form.cleaned_data['goal'])
                    settings.append( ('GOAL_NAME', goal.name, 'EXPERIMENT_SETUP') )
                    
                    environment = Environment.objects.get(id=form.cleaned_data['environment'])
                    settings.append( ('ENVIRONMENT_NAME', environment.name, 'EXPERIMENT_SETUP') )
                    
                    predictor = Goalplanner.objects.get(id=form.cleaned_data['predictor'])

                # Schedule the experiment
                schedule_experiment(template, template.experiment_type, experiment_name,
                                    experiment_name, template.heuristics, heuristic_versions,
                                    [], settings, predictor, user=request.user)
    
                # Return to the list of experiments
                return HttpResponseRedirect('/experiments/private/')


    # Retrieve the databases (if necessary)
    databases_list = []
    selected_database = -1
    selected_labels = '-1 -1'
    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        databases_list = Database.objects.filter(task__type=task_type).order_by('name')
        if reference_experiment is not None:
            try:
                db = databases_list.get(name=reference_experiment.configuration.databaseName())
                selected_database = db.id

                labels = reference_experiment.configuration.labels()
                if len(labels) > 0:
                    selected_labels = ' '.join(labels)
                else:
                    selected_labels = ' '.join(map(lambda x: str(x.index), db.labels.all()))
            except:
                pass


    # Retrieve the goal-planning tasks (if necessary)
    goalplanning_tasks_list = []
    selected_goalplanning_task = -1
    selected_goalplanning_goal = -1
    selected_goalplanning_environment = -1
    if task_type == Task.TYPE_GOALPLANNING:
        goalplanning_tasks_list = Task.objects.filter(type=task_type).order_by('name')
        if reference_experiment is not None:
            try:
                selected_goalplanning_task = reference_experiment.configuration.task.id
                selected_goalplanning_goal = Task.objects.get(id=selected_goalplanning_task).goals.get(name=reference_experiment.configuration.goalName()).id
                selected_goalplanning_environment = Goal.objects.get(id=selected_goalplanning_goal).environments.get(name=reference_experiment.configuration.environmentName()).id
            except:
                pass


    # Retrieve the list of enabled predictors
    selected_predictor = -1
    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        predictors = Task.objects.get(type=task_type).classifiers.filter(status=Classifier.ENABLED).order_by('author__username').order_by('name')
    elif task_type == Task.TYPE_GOALPLANNING:

        class task_predictors_link:
            pass

        predictors = []
        for task in goalplanning_tasks_list:
            l = task_predictors_link()
            l.task = task.name
            l.predictors = task.goalplanners.filter(status=Goalplanner.ENABLED).order_by('author__username').order_by('name')
            predictors.append(l)


    if reference_experiment is not None:
        try:
            if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
                available_predictors = predictors
            elif task_type == Task.TYPE_GOALPLANNING:
                selected_task_name = Task.objects.get(id=selected_goalplanning_task).name
                available_predictors = filter(lambda x: x.task == selected_task_name, predictors)[0].predictors

            fullname = reference_experiment.configuration.predictorName()
            (author, name) = fullname.split('/')

            selected_predictor = available_predictors.get(author__username=author, name=name).id
        except:
            pass

    
    # Retrieve the list of heuristics
    own_latest_heuristic_versions = []
    own_all_heuristic_versions = []
    latest_heuristic_versions = []
    all_heuristic_versions = []
    
    heuristics = Heuristic.objects.filter(author=request.user)
    
    for heuristic in heuristics:
        latest_version = heuristic.latest_version()
        if latest_version is None:
            continue
        
        if latest_version.status == HeuristicVersion.STATUS_OK:
            own_latest_heuristic_versions.append({'id':latest_version.id, 'name':heuristic.name})
            for version in heuristic.versions.iterator():
                if version.status == HeuristicVersion.STATUS_OK:
                    own_all_heuristic_versions.append({'id':version.id, 'name':version.shortname()})

    heuristics = Heuristic.objects.exclude(author=request.user).filter(latest_public_version__isnull=False)
    
    for heuristic in heuristics:
        if heuristic.latest_version().status == HeuristicVersion.STATUS_OK:
            latest_heuristic_versions.append({'id':heuristic.latest_version().id, 'name':heuristic.fullname()})
            for version in heuristic.versions.iterator():
                if version.status == HeuristicVersion.STATUS_OK:
                    all_heuristic_versions.append({'id':version.id, 'name':version.fullname()})

    heuristics_cmp = lambda x, y: cmp(x['name'], y['name'])

    own_latest_heuristic_versions.sort(cmp=heuristics_cmp)
    own_all_heuristic_versions.sort(cmp=heuristics_cmp)
    latest_heuristic_versions.sort(cmp=heuristics_cmp)
    all_heuristic_versions.sort(cmp=heuristics_cmp)


    # Initialisations
    if form is not None:
        data = form.data
        if hasattr(form, 'cleaned_data'):
            data = form.cleaned_data
            
        if data.has_key('database'):
            selected_database = int(data['database'])

        if data.has_key('task_type'):
            selected_goalplanning_task = int(data['task_type'])

        if data.has_key('goal'):
            selected_goalplanning_goal = int(data['goal'])

        if data.has_key('environment'):
            selected_goalplanning_environment = int(data['environment'])

        if data.has_key('predictor'):
            selected_predictor = int(data['predictor'])

    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        if (selected_database == -1) and (len(databases_list) > 0):
            selected_database = databases_list[0].id

        if (selected_predictor == -1) and (predictors.count() > 0):
            selected_predictor = predictors[0].id

    elif task_type == Task.TYPE_GOALPLANNING:
        if (selected_goalplanning_task == -1) and (len(goalplanning_tasks_list) > 0):
            selected_goalplanning_task = goalplanning_tasks_list[0].id

        if (selected_goalplanning_task >= 0) and (selected_goalplanning_goal == -1) and (Task.objects.get(id=selected_goalplanning_task).goals.count() > 0):
            selected_goalplanning_goal = Task.objects.get(id=selected_goalplanning_task).goals.all()[0].id

        if (selected_goalplanning_task >= 0) and (selected_goalplanning_goal >= 0) and \
           (selected_goalplanning_environment == -1) and (Goal.objects.get(id=selected_goalplanning_goal).environments.count() > 0):
            selected_goalplanning_environment = Goal.objects.get(id=selected_goalplanning_goal).environments.all()[0].id

        if (selected_predictor == -1) and (filter(lambda x: x.task == Task.objects.get(id=selected_goalplanning_task).name, predictors)[0].predictors.count() > 0):
            selected_predictor = filter(lambda x: x.task == Task.objects.get(id=selected_goalplanning_task).name, predictors)[0].predictors[0].id

    if form is None:
        data = {
            'name': '',
            'predictor': selected_predictor,
            'heuristics': '-1',
            'show_all_versions': 0,
            'predictor_settings': '',
            'heuristics_type': Configuration.CUSTOM_HEURISTICS_LIST,
        }

        if reference_experiment is not None:
            data['name'] = reference_experiment.name + ' (copy)'
            data['heuristics'] = ' '.join(map(lambda x: str(x.id), reference_experiment.configuration.heuristics_set.all()))
            data['show_all_versions'] = reduce(lambda x, y: x or ((y.heuristic.author == request.user) and (y.heuristic.latest_version().version > y.version)) or ((y.heuristic.author != request.user) and (y.heuristic.latest_public_version.version > y.version)), reference_experiment.configuration.heuristics_set.all(), False)
            data['predictor_settings'] = reference_experiment.configuration.predictorSettings()
            
            if data['show_all_versions']:
                data['show_all_versions'] = 1
            else:
                data['show_all_versions'] = 0

        if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
            data['database'] = selected_database
            data['labels'] = selected_labels
            data['training_ratio'] = 0.5
            
            if selected_database != -1:
                if reference_experiment is not None:
                    if reference_experiment.configuration.useStandardSets() and databases_list.filter(pk=selected_database)[0].has_standard_sets:
                        data['use_standard_sets'] = True
                    else:
                        data['use_standard_sets'] = False
                        data['training_ratio'] = reference_experiment.configuration.trainingRatio()
                else:
                    data['use_standard_sets'] = databases_list.filter(pk=selected_database)[0].has_standard_sets
            else:
                data['use_standard_sets'] = False
            
            form = NewImageBasedExperimentForm(data)
            form.detection = (task_type == Task.TYPE_OBJECT_DETECTION)

        elif task_type == Task.TYPE_GOALPLANNING:
            data['task_type']   = selected_goalplanning_task
            data['goal']        = selected_goalplanning_goal
            data['environment'] = selected_goalplanning_environment

            form = NewGoalplanningExperimentForm(data)

    # Rendering
    return render_to_response('experiments/schedule.html',
                              { 'form': form,
                                'experiment_type': 'private',
                                'experiment_is_advanced': False,
                                'task_type': task_type,
                                
                                'databases_list': databases_list,
                                'selected_database': selected_database,

                                'goalplanning_tasks_list': goalplanning_tasks_list,
                                'selected_goalplanning_task': selected_goalplanning_task,
                                'selected_goalplanning_goal': selected_goalplanning_goal,
                                'selected_goalplanning_environment': selected_goalplanning_environment,
                                
                                'own_latest_heuristic_versions': own_latest_heuristic_versions,
                                'own_all_heuristic_versions': own_all_heuristic_versions,
                                'latest_heuristic_versions': latest_heuristic_versions,
                                'all_heuristic_versions': all_heuristic_versions,
                                'predictors': predictors,
                                'selected_predictor': selected_predictor,
                                'max_nb_public_heuristics': MAX_NB_PUBLIC_HEURISTICS_IN_PRIVATE_EXPERIMENTS,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Used to schedule an advanced experiment
#---------------------------------------------------------------------------------------------------
@login_required
def experiments_schedule_advanced(request, experiment_type):

    # Check that the user can do that
    if not(request.user.get_profile().project_member):
        raise Http404

    # Retrieve the reference experiment (if any)
    reference_experiment = None
    if request.GET.has_key('ref'):
        try:
            reference_experiment = Experiment.objects.get(id=int(request.GET['ref']))
            if not(reference_experiment.isPublic() or reference_experiment.isConsortium()):
                reference_experiment = None
        except:
            pass

    # Retrieve the type of task
    if reference_experiment is None:
        task_type = Task.TYPE_CLASSIFICATION
        if request.GET.has_key('t'):
            task_type = request.GET['t']
            if task_type not in [Task.TYPE_CLASSIFICATION, Task.TYPE_OBJECT_DETECTION, Task.TYPE_GOALPLANNING]:
                task_type = Task.TYPE_CLASSIFICATION
    else:
        task_type = reference_experiment.configuration.task.type

    # Process the form
    form = None
    if (request.method == 'POST') and request.POST.has_key('submit'):
    
        if request.POST['submit'] == 'Cancel':
            return HttpResponseRedirect('/experiments/consortium/')
    
        if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
            form = NewImageBasedExperimentForm(request.POST)
            form.detection = (task_type == Task.TYPE_OBJECT_DETECTION)

        elif task_type == Task.TYPE_GOALPLANNING:
            form = NewGoalplanningExperimentForm(request.POST)

        if form.is_valid() and (request.POST['submit'] == 'Schedule'):
    
            if task_type == Task.TYPE_CLASSIFICATION:
                template_name = 'classification'
            elif task_type == Task.TYPE_OBJECT_DETECTION:
                template_name = 'detection'
            elif task_type == Task.TYPE_GOALPLANNING:
                template_name = 'goalplanning'
    
            # Retrieve the configuration template (all the advanced configuration use the consortium templates)
            if task_type == Task.TYPE_GOALPLANNING:
                template = Configuration.objects.filter(name='template/%s' % template_name).filter(experiment_type=Configuration.CONSORTIUM, task=form.cleaned_data['task_type'])[0]
            else:
                template = Configuration.objects.filter(name='template/%s' % template_name).filter(experiment_type=Configuration.CONSORTIUM)[0]

            # Retrieve the name, generate one if necessary
            experiment_name = form.cleaned_data['name']
            if len(experiment_name) == 0:
                experiment_name = '%s/%d' % (template_name, Experiment.objects.filter(configuration__experiment_type=experiment_type,
                                                                                      user=request.user,
                                                                                      configuration__task__type=template.task.type).count() + 1)

            if (experiment_type == Configuration.CONTEST_BASE) and not(experiment_name.endswith('/base')):
                experiment_name += '/base'

            # Retrieve the list of heuristic versions to use
            heuristic_versions = None
            heuristics_type = form.cleaned_data['heuristics_type']
            if heuristics_type == Configuration.CUSTOM_HEURISTICS_LIST:
                heuristic_versions = HeuristicVersion.objects.filter(id__in=form.cleaned_data['heuristics'].split(' '))
            elif heuristics_type == Configuration.LATEST_VERSION_ALL_HEURISTICS:
                heuristics = Heuristic.objects.filter(latest_public_version__isnull=False).filter(latest_public_version__status=HeuristicVersion.STATUS_OK)
                heuristic_versions = map(lambda x: x.latest_public_version, heuristics)
            elif heuristics_type == Configuration.ALL_VERSIONS_ALL_HEURISTICS:
                heuristic_versions = HeuristicVersion.objects.filter(public=True).filter(status=HeuristicVersion.STATUS_OK)

            # Retrieve the settings and the predictor to use
            settings = []
            predictor = None

            if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
                db = Database.objects.get(id=form.cleaned_data['database'])
                settings.append( ('DATABASE_NAME', db.name, 'EXPERIMENT_SETUP') )

                if not(db.has_standard_sets) or not(form.cleaned_data['use_standard_sets']):
                    settings.append( ('TRAINING_SAMPLES', form.cleaned_data['training_ratio'], 'EXPERIMENT_SETUP') )
            
                settings.append( ('LABELS', form.cleaned_data['labels'], 'EXPERIMENT_SETUP') )

                predictor = Classifier.objects.get(id=form.cleaned_data['predictor'])

            elif task_type == Task.TYPE_GOALPLANNING:
                goal = Goal.objects.get(id=form.cleaned_data['goal'])
                settings.append( ('GOAL_NAME', goal.name, 'EXPERIMENT_SETUP') )

                environment = Environment.objects.get(id=form.cleaned_data['environment'])
                settings.append( ('ENVIRONMENT_NAME', environment.name, 'EXPERIMENT_SETUP') )

                predictor = Goalplanner.objects.get(id=form.cleaned_data['predictor'])

            if len(form.cleaned_data['predictor_settings']) > 0:
                lines = form.cleaned_data['predictor_settings'].split('\n')
                lines = filter(lambda x: len(x) > 0, lines)
                for line in lines:
                    parts = line.split(' ')
                    parts = filter(lambda x: len(x) > 0, parts)
                    if len(parts) > 0:
                        settings.append( (parts[0], ' '.join(parts[1:]), 'PREDICTOR_SETUP') )

            # Schedule the experiment
            schedule_experiment(template, experiment_type, experiment_name,
                                experiment_name, heuristics_type,
                                heuristic_versions, [], settings, predictor,
                                user=request.user)
    
            # Return to the list of experiments
            if experiment_type == Configuration.CONTEST_BASE:
                return HttpResponseRedirect('/experiments/contest/')
            else:
                return HttpResponseRedirect('/experiments/consortium/')


    # Retrieve the databases (if necessary)
    databases_list = []
    selected_database = -1
    selected_labels = '-1 -1'
    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        databases_list = Database.objects.filter(task__type=task_type).order_by('name')
        if reference_experiment is not None:
            try:
                db = databases_list.get(name=reference_experiment.configuration.databaseName())
                selected_database = db.id

                labels = reference_experiment.configuration.labels()
                if len(labels) > 0:
                    selected_labels = ' '.join(labels)
                else:
                    selected_labels = ' '.join(map(lambda x: str(x.index), db.labels.all()))
            except:
                pass


    # Retrieve the goal-planning tasks (if necessary)
    goalplanning_tasks_list = []
    selected_goalplanning_task = -1
    selected_goalplanning_goal = -1
    selected_goalplanning_environment = -1
    if task_type == Task.TYPE_GOALPLANNING:
        goalplanning_tasks_list = Task.objects.filter(type=task_type).order_by('name')
        if reference_experiment is not None:
            try:
                selected_goalplanning_task = reference_experiment.configuration.task.id
                selected_goalplanning_goal = Task.objects.get(id=selected_goalplanning_task).goals.get(name=reference_experiment.configuration.goalName()).id
                selected_goalplanning_environment = Goal.objects.get(id=selected_goalplanning_goal).environments.get(name=reference_experiment.configuration.environmentName()).id
            except:
                pass


    # Retrieve the list of enabled predictors
    selected_predictor = -1
    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        predictors = Task.objects.get(type=task_type).classifiers.exclude(status=Classifier.DISABLED).exclude(status=Classifier.SYSTEM).order_by('author__username').order_by('name')
    elif task_type == Task.TYPE_GOALPLANNING:

        class task_predictors_link:
            pass

        predictors = []
        for task in goalplanning_tasks_list:
            l = task_predictors_link()
            l.task = task.name
            l.predictors = task.goalplanners.exclude(status=Goalplanner.DISABLED).order_by('author__username').order_by('name')
            predictors.append(l)


    if reference_experiment is not None:
        try:
            if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
                available_predictors = predictors
            elif task_type == Task.TYPE_GOALPLANNING:
                selected_task_name = Task.objects.get(id=selected_goalplanning_task).name
                available_predictors = filter(lambda x: x.task == selected_task_name, predictors)[0].predictors

            fullname = reference_experiment.configuration.predictorName()
            (author, name) = fullname.split('/')

            selected_predictor = available_predictors.get(author__username=author, name=name).id
        except:
            pass


    # Retrieve the list of heuristics
    latest_heuristic_versions = []
    all_heuristic_versions = []

    heuristics = Heuristic.objects.filter(latest_public_version__isnull=False)
    
    for heuristic in heuristics:
        if heuristic.latest_public_version.status == HeuristicVersion.STATUS_OK:
            latest_heuristic_versions.append({'id':heuristic.latest_public_version.id, 'name':heuristic.fullname()})
            for version in heuristic.versions.iterator():
                if version.public and (version.status == HeuristicVersion.STATUS_OK):
                    all_heuristic_versions.append({'id':version.id, 'name':version.fullname()})

    heuristics_cmp = lambda x, y: cmp(x['name'], y['name'])

    latest_heuristic_versions.sort(cmp=heuristics_cmp)
    all_heuristic_versions.sort(cmp=heuristics_cmp)

    # Initialisations
    if form is not None:
        data = form.data
        if hasattr(form, 'cleaned_data'):
            data = form.cleaned_data
            
        if data.has_key('database'):
            selected_database = int(data['database'])

        if data.has_key('task_type'):
            selected_goalplanning_task = int(data['task_type'])

        if data.has_key('goal'):
            selected_goalplanning_goal = int(data['goal'])

        if data.has_key('environment'):
            selected_goalplanning_environment = int(data['environment'])

        if data.has_key('predictor'):
            selected_predictor = int(data['predictor'])

    if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
        if (selected_database == -1) and (len(databases_list) > 0):
            selected_database = databases_list[0].id

        if (selected_predictor == -1) and (predictors.count() > 0):
            selected_predictor = predictors[0].id

    elif task_type == Task.TYPE_GOALPLANNING:
        if (selected_goalplanning_task == -1) and (len(goalplanning_tasks_list) > 0):
            selected_goalplanning_task = goalplanning_tasks_list[0].id

        if (selected_goalplanning_task >= 0) and (selected_goalplanning_goal == -1) and (Task.objects.get(id=selected_goalplanning_task).goals.count() > 0):
            selected_goalplanning_goal = Task.objects.get(id=selected_goalplanning_task).goals.all()[0].id

        if (selected_goalplanning_task >= 0) and (selected_goalplanning_goal >= 0) and \
           (selected_goalplanning_environment == -1) and (Goal.objects.get(id=selected_goalplanning_goal).environments.count() > 0):
            selected_goalplanning_environment = Goal.objects.get(id=selected_goalplanning_goal).environments.all()[0].id

        if (selected_predictor == -1) and (filter(lambda x: x.task == Task.objects.get(id=selected_goalplanning_task).name, predictors)[0].predictors.count() > 0):
            selected_predictor = filter(lambda x: x.task == Task.objects.get(id=selected_goalplanning_task).name, predictors)[0].predictors[0].id

    if form is None:
        data = {
            'name': '',
            'predictor': selected_predictor,
            'heuristics': '-1',
            'show_all_versions': 0,
            'predictor_settings': '',
            'heuristics_type': Configuration.LATEST_VERSION_ALL_HEURISTICS,
        }

        if reference_experiment is not None:
            data['name'] = reference_experiment.name + ' (copy)'
            data['heuristics'] = ' '.join(map(lambda x: str(x.id), reference_experiment.configuration.heuristics_set.all()))
            data['show_all_versions'] = reduce(lambda x, y: x or (y.heuristic.latest_public_version.version > y.version), reference_experiment.configuration.heuristics_set.all(), False)
            data['predictor_settings'] = reference_experiment.configuration.predictorSettings()
            data['heuristics_type'] = Configuration.CUSTOM_HEURISTICS_LIST
            
            if data['show_all_versions']:
                data['show_all_versions'] = 1
            else:
                data['show_all_versions'] = 0

        if (task_type == Task.TYPE_CLASSIFICATION) or (task_type == Task.TYPE_OBJECT_DETECTION):
            data['database'] = selected_database
            data['labels'] = selected_labels
            data['training_ratio'] = 0.5
            
            if selected_database != -1:
                if reference_experiment is not None:
                    if reference_experiment.configuration.useStandardSets() and databases_list.filter(pk=selected_database)[0].has_standard_sets:
                        data['use_standard_sets'] = True
                    else:
                        data['use_standard_sets'] = False
                        data['training_ratio'] = reference_experiment.configuration.trainingRatio()
                else:
                    data['use_standard_sets'] = databases_list.filter(pk=selected_database)[0].has_standard_sets
            else:
                data['use_standard_sets'] = False
            
            form = NewImageBasedExperimentForm(data)
            form.detection = (task_type == Task.TYPE_OBJECT_DETECTION)

        elif task_type == Task.TYPE_GOALPLANNING:
            data['task_type']   = selected_goalplanning_task
            data['goal']        = selected_goalplanning_goal
            data['environment'] = selected_goalplanning_environment

            form = NewGoalplanningExperimentForm(data)

    if experiment_type == Configuration.CONSORTIUM:
        experiment_type_name = 'consortium'
    else:
        experiment_type_name = 'contest'

    # Rendering
    return render_to_response('experiments/schedule.html',
                              { 'form': form,
                                'experiment_type': experiment_type_name,
                                'experiment_is_advanced': True,
                                'task_type': task_type,

                                'databases_list': databases_list,
                                'selected_database': selected_database,

                                'goalplanning_tasks_list': goalplanning_tasks_list,
                                'selected_goalplanning_task': selected_goalplanning_task,
                                'selected_goalplanning_goal': selected_goalplanning_goal,
                                'selected_goalplanning_environment': selected_goalplanning_environment,

                                'latest_heuristic_versions': latest_heuristic_versions,
                                'all_heuristic_versions': all_heuristic_versions,
                                'predictors': predictors,
                                'selected_predictor': selected_predictor,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Delete/Cancel an experiment
#---------------------------------------------------------------------------------------------------
@login_required
def delete_experiment(request, experiment_id):

    # Retrieve the experiment
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    # Check that the user can do that
    if not(request.user.is_superuser) and (request.user != experiment.user):
        raise Http404

    # Mark the experiment as deleted anymore
    experiment.status = Experiment.STATUS_DELETED
    experiment.save()

    # Retrieve the experiment again (in case the Experiment Scheduler updated the status since the last update)
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    # Tell the Experiments Scheduler to cancel the experiment
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand(Message('CANCEL_EXPERIMENT', [experiment.id]))
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)

    # If the experiment isn't in 'scheduled' state, we keep it in the database
    if experiment.isScheduled():
    
        # We keep the error reports, but remove their link with the experiment
        for error_report in experiment.error_reports.all():
            error_report.experiment = None
            error_report.save()

        # Delete the experiment
        configuration = experiment.configuration
        experiment.delete()
        configuration.delete()

    return HttpResponseRedirect('/experiments/')


#---------------------------------------------------------------------------------------------------
# Handle the creation of/redirection to the official forum topic of a heuristic
#---------------------------------------------------------------------------------------------------
def topic(request, experiment_id):

    # Retrieve the experiment
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    # Create the experiment topic if it don't already exists
    if experiment.post is None:
        if (experiment.configuration.experiment_type == Configuration.PUBLIC) or \
           (experiment.configuration.experiment_type == Configuration.CONTEST_BASE) or \
           (experiment.configuration.experiment_type == Configuration.CONTEST_ENTRY):
            forum_name = 'Experiments'
        elif experiment.configuration.experiment_type == Configuration.CONSORTIUM:
            forum_name = 'Consortium experiments'
        else:
            raise Http404

        createTopic(experiment, forum_name, experiment.fullname(),
                    'experiments/%d/' % experiment.id, 'experiment')

    # Go to the topic
    return HttpResponseRedirect('/forum/viewtopic.php?t=%d' % experiment.post.topic.topic_id)

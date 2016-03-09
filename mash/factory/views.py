# Create your views here.
f################################################################################
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


rom django.utils import simplejson
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import defaultfilters
from django.core.files import locks
from mash.accounts.models import UserProfile
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.utilities import *
from mash.experiments.views import schedule_experiment
from mash.experiments.models import Configuration, Setting, Experiment
from mash.experiments.models import GoalPlanningResult, GoalPlanningRound
from mash.factory.models import FactoryTask, FactoryTaskResult, DebuggingEntry
from mash.instruments.models import DataReport
from mash.instruments.views import get_snippets_static_files
from mash.instruments.views import get_or_create_snippet
from mash.instruments.views import snippet as html_snippet
from mash.instruments.models import View
from pymash.gitrepository import GitRepository
from pymash.messages import Message
from servers import acquireExperimentsScheduler, releaseExperimentsScheduler
from datetime import datetime, date, timedelta
import os
import shutil
import tarfile
import math
from operator import itemgetter, attrgetter
import struct
import base64


# Constants
ATTRIBUTES_BEGIN_SEARCH       = "///ATTRIBUTES_BEGIN"
ATTRIBUTES_END_SEARCH         = "///ATTRIBUTES_END"

DIM_BEGIN_SEARCH              = "///DIM_BEGIN"
DIM_END_SEARCH                = "///DIM_END"

INIT_BEGIN_SEARCH             = "///INIT_BEGIN"
INIT_END_SEARCH               = "///INIT_END"

COMPUTE_FEATURES_BEGIN_SEARCH = "///COMPUTE_FEATURES_BEGIN"
COMPUTE_FEATURES_END_SEARCH   = "///COMPUTE_FEATURES_END"

TERMINATE_BEGIN_SEARCH        = "///TERMINATE_BEGIN"
TERMINATE_END_SEARCH          = "///TERMINATE_END"


def process_cookie(request):
    cookie_value = ""
    user = request.user
    if request.COOKIES.has_key('robot_uid'):
        cookie_value = request.COOKIES.__getitem__('robot_uid')

        if cookie_value != "REGISTERED_USER":

            # Retrieve the user account
            if user.is_anonymous():
                username = "anon_%s" % cookie_value

                try :
                    # Check if the anonymous user has already used the system
                    user = User.objects.all().get(username=username)
                except User.DoesNotExist :
                    # Create an user account associated with the cookie
                    user = User.objects.create_user(username, '', '')
                    user.is_active = True
                    user.save()

    return user


def json_response(content):
    response = HttpResponse(mimetype="text/plain")

    # Prevent ajax cache in IE8
    response["Cache-Control"] = "max-age=0,no-cache,no-store"

    if isinstance(content, dict): 
        response.write(simplejson.dumps(content))
    else :
        response.write(content)

    return response


def text_response(content):
    response = HttpResponse(mimetype="text/plain")

    # Prevent ajax cache in IE8
    response["Cache-Control"] = "max-age=0,no-cache,no-store"

    response.write(content)

    return response


def menu_status(user):
    status = {
        'compilation': 0,
        'experiments': 0,
        'recorded_data': None,
        'heuristic_unchecked': 0,
        'nb_compilation_errors': 0,
        'nb_total_numbers_heuristics': 0,
        'heuristic_ids': {
            'errors': [],
            'in_progress': [],
        },
    }

    if not(user.is_anonymous()):

        heuristic_test_status = HeuristicTestStatus.objects.filter(heuristic_version__heuristic__simple=True,
                                                                   heuristic_version__heuristic__author=user,
                                                                   heuristic_version__checked=False,
                                                                   error=False)
        status['compilation'] = heuristic_test_status.count()

        task_results = FactoryTaskResult.objects.filter(experiment__user=user)
        status['experiments'] = task_results.filter(Q(experiment__status=Experiment.STATUS_SCHEDULED) |
                                                    Q(experiment__status=Experiment.STATUS_RUNNING)).count()

        status['heuristic_ids']['errors'] = \
                map(lambda x: x.heuristic_version.id,
                    HeuristicTestStatus.objects.filter(heuristic_version__heuristic__author__id=user.id,
                                                       heuristic_version__heuristic__simple=True,
                                                       heuristic_version__checked=False,
                                                       error=True))

        status['heuristic_ids']['in_progress'] = \
                map(lambda x: x.heuristic_version.id,
                    HeuristicTestStatus.objects.filter(heuristic_version__heuristic__author__id=user.id,
                                                       heuristic_version__heuristic__simple=True,
                                                       heuristic_version__checked=False,
                                                       error=False))

        status['nb_compilation_errors'] = len(status['heuristic_ids']['errors'])
        status['nb_total_numbers_heuristics'] = HeuristicVersion.objects.filter(heuristic__simple=True,
                                                                                heuristic__author=user).count()

        try:
            debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)
            if (debugging_entry.status == DebuggingEntry.STATUS_DONE) or \
               (debugging_entry.status == DebuggingEntry.STATUS_FAILED):
                status['recorded_data'] = 'done'
            else:
                status['recorded_data'] = 'running'
        except:
            pass

    status['heuristic_unchecked'] = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True).exclude(checked=True).count()

    return status


def factory(request):
    tutorialMode = int(0)
    debugMode    = int(0)
    finalMode    = int(0)
    try:
        if (request.GET['tutorialMode'] == 'on') :
            tutorialMode = int(1)
    except:
        tutorialMode = int(0)
    try:
        if (request.GET['debugMode'] == 'on') :
            debugMode = int(1)
    except:
        debugMode = int(0)
    try:
        if (request.GET['finalMode'] == 'on') :
            finalMode = int(1)
    except:
        finalMode = int(0)


    user = process_cookie(request)

    nbTotalTask = FactoryTask.objects.all().order_by('taskNumber').count()
    #only display simple heuristics from current user
    heuristiclist = []
    if not user.is_anonymous():
        heuristiclist = HeuristicVersion.objects.filter(heuristic__simple=True, heuristic__author=user).order_by('heuristic__name')

    heuristiclist_status = False
    if not heuristiclist:
        heuristiclist_status = False
    else:
        heuristiclist_status = True

    return render_to_response('factory/programming.html',
                              {
                                'anonymous': user.is_anonymous(),
                                'phases': HeuristicTestStatus.PHASES,
                                'heuristiclist':heuristiclist,
                                'heuristiclist_status':heuristiclist_status,
                                'debugging_entry': None,
                                'menu_status': menu_status(user),
                                'nb_task': nbTotalTask,
                                'tutorial_mode': tutorialMode,
                                'debug_mode': debugMode,
                                'final_mode': finalMode,
                              },
                              context_instance=RequestContext(request))


def tasks(request):
    tutorialMode = int(0)
    debugMode    = int(0)
    try:
        if (request.GET['tutorialMode'] == 'on') :
            tutorialMode = int(1)
    except:
        tutorialMode = int(0)
    try:
        if (request.GET['debugMode'] == 'on') :
            debugMode = int(1)
    except:
        debugMode = int(0)

    user = process_cookie(request)

    factoryTasks   = FactoryTask.objects.all().order_by('taskNumber')
    if not(user.is_anonymous()):
        heuristic_list = HeuristicVersion.objects.filter(heuristic__simple=True, heuristic__author=user, checked=True).order_by('heuristic__name')
    else:
        heuristic_list = []

    # Retrieve the CSS and JS files needed by the snippets of the instruments used by the experiments (if any)
    snippets_css_files = []
    snippets_js_files = []
    try:
        for instrument in factoryTasks[0].config.instruments_set.iterator():
            (instrument_css_files, instrument_js_files) = get_snippets_static_files(instrument)

            snippets_css_files.extend(filter(lambda x: x not in snippets_css_files, instrument_css_files))
            snippets_js_files.extend(filter(lambda x: x not in snippets_js_files, instrument_js_files))
    except:
        pass

    instrument_views = []
    try:
        for instrument in factoryTasks[0].config.instruments_set.iterator():
            instrument_views.extend(View.objects.filter(instrument=instrument, used_in_factory_results=True))
    except:
        pass

    return render_to_response('factory/tasks.html',
                              {
                                  'factoryTasks':   factoryTasks,
                                  'heuristic_list': heuristic_list,
                                  'debugging_entry': None,
                                  'snippets_css_files': snippets_css_files,
                                  'snippets_js_files': snippets_js_files,
                                  'instrument_views': instrument_views,
                                  'menu_status': menu_status(user),
                                  'tutorial_mode': tutorialMode,
                                  'debug_mode': debugMode,
                              },
                              context_instance=RequestContext(request))


def last_recorded_data(request):
    user = process_cookie(request)

    if user.is_anonymous():
        raise Http404

    factoryTasks   = FactoryTask.objects.all().order_by('taskNumber')
    heuristic_list = HeuristicVersion.objects.filter(heuristic__simple=True, heuristic__author=user, checked=True).order_by('heuristic__name')

    # Retrieve the CSS and JS files needed by the snippets of the instruments used by the experiments (if any)
    snippets_css_files = []
    snippets_js_files = []
    try:
        for instrument in factoryTasks[0].config.instruments_set.iterator():
            (instrument_css_files, instrument_js_files) = get_snippets_static_files(instrument)

            snippets_css_files.extend(filter(lambda x: x not in snippets_css_files, instrument_css_files))
            snippets_js_files.extend(filter(lambda x: x not in snippets_js_files, instrument_js_files))
    except:
        pass

    instrument_views = []
    try:
        for instrument in factoryTasks[0].config.instruments_set.iterator():
            instrument_views.extend(View.objects.filter(instrument=instrument, used_in_factory_results=True))
    except:
        pass

    debugging_entry = None
    try:
        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)
    except:
        pass

    return render_to_response('factory/tasks.html',
                              {
                                  'factoryTasks':   factoryTasks,
                                  'heuristic_list': heuristic_list,
                                  'debugging_entry': debugging_entry,
                                  'snippets_css_files': snippets_css_files,
                                  'snippets_js_files': snippets_js_files,
                                  'instrument_views': instrument_views,
                                  'menu_status': menu_status(user),
                              },
                              context_instance=RequestContext(request))


def groups(request):
    user = process_cookie(request)

    leaded_groups = user.get_profile().leaded_groups()
    if len(leaded_groups) == 0:
        raise Http404

    factoryTasks = FactoryTask.objects.all().order_by('taskNumber')

    groups = []
    for leaded_group in leaded_groups:

        from django.db import connection, transaction
        cursor = connection.cursor()

        cursor.execute("SELECT user_id " \
                       "FROM phpbb_user_group " \
                       "WHERE group_id=%d "\
                         "AND user_pending=0 " \
                         "AND group_leader=0" % leaded_group.group_id)

        members = map(lambda x: x.user,
                      UserProfile.objects.filter(
                                forum_user__user_id__in=map(lambda x: x[0], cursor.fetchall())))

        tasks = []
        for factory_task in factoryTasks:
            results = FactoryTaskResult.objects.filter(task=factory_task,
                                                       experiment__user__id__in=map(lambda x: x.id, members))

            global_score = 0.0
            users = []
            for task_result in results:
                try:
                    result = task_result.experiment.goalplanning_results.all()[0]
                except:
                    continue

                score = 100.0 * float(result.nbActionsDone - result.nbMimickingErrors) / result.nbActionsDone
                global_score += score

                user_entry = {
                    'id':            task_result.experiment.user.id,
                    'name':          '%s %s (%s)' % (task_result.experiment.user.last_name,
                                                     task_result.experiment.user.first_name,
                                                     task_result.experiment.user.username),
                    'nb_heuristics': result.experiment.configuration.heuristics_set.count(),
                    'score':         score,
                }

                users.append(user_entry)

            user_ids = map(lambda x: x['id'], users)
            missing_users = filter(lambda x: not(x.id in user_ids), members)
            for missing_user in missing_users:
                user_entry = {
                    'id':            missing_user.id,
                    'name':          '%s %s (%s)' % (missing_user.last_name,
                                                     missing_user.first_name,
                                                     missing_user.username),
                    'nb_heuristics': 0,
                    'score':         None,
                }

                users.append(user_entry)

            users.sort(cmp=lambda x, y: cmp(x['name'], y['name']))

            global_score /= len(members)

            task = {
                'task':         factory_task,
                'global_score': global_score,
                'users':        users,
            }

            tasks.append(task)

        group = {
            'name':  leaded_group.group_name,
            'tasks': tasks,
        }

        groups.append(group)

    return render_to_response('factory/groups.html',
                              { 'groups': groups,
                                'menu_status': menu_status(user),
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Delete a specific simple heuristic
#---------------------------------------------------------------------------------------------------
def delete(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    try:
        version_id = int(request.GET['id'])
    except:
        raise Http404

    user = process_cookie(request)

    # Retrieve the version
    if version_id != -1:
        version = get_object_or_404(HeuristicVersion, pk=version_id)
    else:
        raise Http404

    # Check that the user has the right to delete the version
    if ((user != version.heuristic.author) and not(user.is_superuser)) or version.public:
        raise Http404

    # Retrieve the repository containing the source file and lock it
    if version.checked:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
    else:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
    repo.lock()

    try:
        # Remove the file from the repository
        repo.removeFile('%s/%s' % (user.username.lower(), version.filename),
                        "Heuristic '%s' deleted (by %s)" % (version.fullname(), user.username),
                        settings.COMMIT_AUTHOR)
    except:
        pass

    # Release the lock
    repo.unlock()

    # Delete the relevant entries from the database
    try:
        HeuristicTestStatus.objects.filter(heuristic_version__exact=version).delete()
    except:
        pass

    version.delete()

    return json_response(menu_status(user))


#---------------------------------------------------------------------------------------------------
# Display heuristics code in box
#---------------------------------------------------------------------------------------------------
def retrieve_source_code(request):

    class _SourceCodeInfo:
        def __init__(self):
            self.first_line = 0
            self.code = ''


    user = process_cookie(request)

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    if request.GET.has_key('id'):
        version_id = request.GET['id']
    else:
        raise Http404

    # Retrieve the version
    if version_id != "-1":
        version = get_object_or_404(HeuristicVersion, pk=version_id)
    else:
        raise Http404

    # Retrieve the source code
    if version.status != HeuristicVersion.STATUS_DELETED:
        source = get_source_code(version)

    attributes      = _SourceCodeInfo()
    dim             = _SourceCodeInfo()
    init            = _SourceCodeInfo()
    computeFeatures = _SourceCodeInfo()
    terminate       = _SourceCodeInfo()

    dest = None

    for index, line in enumerate(source.data.split("\n")):

        if dest is None:
            if line.find(ATTRIBUTES_BEGIN_SEARCH) != -1:
                dest = attributes
            elif line.find(DIM_BEGIN_SEARCH) != -1:
                dest = dim
            elif line.find(INIT_BEGIN_SEARCH) != -1:
                dest = init
            elif line.find(COMPUTE_FEATURES_BEGIN_SEARCH) != -1:
                dest = computeFeatures
            elif line.find(TERMINATE_BEGIN_SEARCH) != -1:
                dest = terminate

            if dest is not None:
                dest.first_line = index + 2
        else:
            if (line.find(ATTRIBUTES_END_SEARCH) != -1) or \
               (line.find(DIM_END_SEARCH) != -1) or \
               (line.find(INIT_END_SEARCH) != -1) or \
               (line.find(COMPUTE_FEATURES_END_SEARCH) != -1) or \
               (line.find(TERMINATE_END_SEARCH) != -1):
                dest = None
            else:
                dest.code += line + '\n'

    response_content = { "checked": version.checked,
                         "attributes": { "first_line": attributes.first_line, "code": attributes.code },
                         "dim": { "first_line": dim.first_line, "code": dim.code },
                         "init": { "first_line": init.first_line, "code": init.code },
                         "computeFeatures": { "first_line": computeFeatures.first_line, "code": computeFeatures.code },
                         "terminate": { "first_line": terminate.first_line, "code": terminate.code },
                         "menu_status": menu_status(user),
                       }



    return json_response(response_content)


#---------------------------------------------------------------------------------------------------
# Handle the upload of a new heuristic
# AJAX: Returns the HTML version of a field value, using the given syntax
#---------------------------------------------------------------------------------------------------
def upload(request):

    class _SourceCodeInfo:
        def __init__(self):
            self.first_line = 0
            self.code = ''


    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    editorsList = []

    try:
        editorsList.append(request.POST['text_attributeseditor'])
        editorsList.append(request.POST['text_dimeditor'])
        editorsList.append(request.POST['text_startruneditor'])
        editorsList.append(request.POST['text_computefeatureseditor'])
        editorsList.append(request.POST['text_endruneditor'])
        heuristic_name = request.POST['heuristic_name']
        heuristic_id = int(request.POST['heuristic_id'])
    except:
        raise Http404

    inputSourceFile = open(os.path.join(settings.MEDIA_ROOT, 'simple_heuristic.cpp'), 'r')
    inputSource = inputSourceFile.readlines()
    inputSourceFile.close()

    user = process_cookie(request)

    # Retrieve the upload repository and lock it
    repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
    repo.lock()
    try:
        # Create it if necessary
        repo.createIfNotExists()

        # Check that the heuristic name is free (we assume that the user wants to create a new heuristic)
        extension = ".cpp"
        heuristic_file_name = '%s%s' % (heuristic_name, extension)

        # Create the user directory in the upload repository if necessary
        user_path = os.path.join(repo.fullpath(), user.username.lower())
        if not(os.path.exists(user_path)):
            os.mkdir(user_path)

        # Write the file into the upload repository
        destination = open(os.path.join(user_path, heuristic_file_name), 'w')

        indexes = {
            ATTRIBUTES_BEGIN_SEARCH: 0,
            DIM_BEGIN_SEARCH: 1,
            INIT_BEGIN_SEARCH: 2,
            COMPUTE_FEATURES_BEGIN_SEARCH: 3,
            TERMINATE_BEGIN_SEARCH: 4,
        }

        source_code_infos = [_SourceCodeInfo(), _SourceCodeInfo(), _SourceCodeInfo(), _SourceCodeInfo(), _SourceCodeInfo()]

        disable_output = False
        line_counter = 0
        for line in inputSource:

            if not(disable_output):
                destination.write(line)
                line_counter += 1

                for (key, index) in indexes.items():
                    if line.find(key) != -1:
                        destination.write(editorsList[index])
                        source_code_infos[index].code = editorsList[index]
                        source_code_infos[index].first_line = line_counter + 1

                        if (len(editorsList[index]) == 0) or (editorsList[index][-1] != '\n'):
                            destination.write("\n")
                            source_code_infos[index].code += "\n"

                        line_counter += len(source_code_infos[index].code.split('\n')) - 1

                        disable_output = True
                        break
            else:
                disable_output = not((line.find(ATTRIBUTES_END_SEARCH) != -1) or \
                                     (line.find(DIM_END_SEARCH) != -1) or \
                                     (line.find(INIT_END_SEARCH) != -1) or \
                                     (line.find(COMPUTE_FEATURES_END_SEARCH) != -1) or \
                                     (line.find(TERMINATE_END_SEARCH) != -1))

                if not(disable_output):
                    destination.write(line)
                    line_counter += 1

        destination.close()

        # Commit the new file
        repo.commitFile('%s/%s' % (user.username.lower(), heuristic_file_name),
                        "'%s' uploaded heuristic '%s'" % (user.username, heuristic_file_name),
                        settings.COMMIT_AUTHOR)

        # Retrieve the git ID of the file
        blob = repo.repository().tree()[user.username.lower()][heuristic_file_name]

        if heuristic_id == -1:
            # Add informations about the heuristic in the database
            heuristic           = Heuristic()
            heuristic.author    = user
            heuristic.name      = heuristic_name
            heuristic.simple    = True
            heuristic.save()

            version             = HeuristicVersion()
            version.heuristic   = heuristic
            version.filename    = heuristic_file_name
            version.upload_date = datetime.now()
            version.status      = HeuristicVersion.STATUS_OK
            version.save()
        else:
            version = HeuristicVersion.objects.get(id=int(heuristic_id))
            version.upload_date = datetime.now()
            version.checked     = False
            version.status      = HeuristicVersion.STATUS_OK
            version.save()

            # Delete the error reports associated with the heuristic version (if any)
            if version.error_reports.count() > 0:
                for error_report in version.error_reports.all():
                    error_report.delete()

            # Mark the debugging entry associated with the heuristic version obsolete (if any)
            try:
                debugging_entry = DebuggingEntry.objects.get(heuristic_version=version)
                debugging_entry.obsolete = True
                debugging_entry.save()
            except:
                pass

        # Mark all the existing factory tasks obsolete (if any)
        task_results = FactoryTaskResult.objects.filter(experiment__user=user, obsolete=False)
        for task_result in task_results:
            task_result.obsolete = True
            task_result.save()

        try:
            test_status = version.test_status
        except:
            test_status                     = HeuristicTestStatus()
            test_status.heuristic_version   = version

        test_status.error   = False
        test_status.details = ""
        test_status.phase   = HeuristicTestStatus.PHASE_STATUS
        test_status.save()

        # Release the lock
        repo.unlock()

        # Tell the experiments scheduler about the new heuristic
        scheduler = acquireExperimentsScheduler()
        if scheduler is not None:
            scheduler.sendCommand(Message('CHECK_HEURISTIC', [version.id]))
            scheduler.waitResponse()
            releaseExperimentsScheduler(scheduler)
    except:
        repo.unlock()
        raise


    response_content = { "version_id": version.id,
                         "attributes": { "first_line": source_code_infos[0].first_line, "code": source_code_infos[0].code },
                         "dim": { "first_line": source_code_infos[1].first_line, "code": source_code_infos[1].code },
                         "init": { "first_line": source_code_infos[2].first_line, "code": source_code_infos[2].code },
                         "computeFeatures": { "first_line": source_code_infos[3].first_line, "code": source_code_infos[3].code },
                         "terminate": { "first_line": source_code_infos[4].first_line, "code": source_code_infos[4].code },
                         "menu_status": menu_status(user),
                       }

    return json_response(response_content)


#def test(request):
#
#    # Only by Ajax
#    if not(request.is_ajax()):
#        raise Http404
#
#    user = process_cookie(request)
#
#    personalConfigurations = Configuration.objects.filter(experiment_type=Configuration.FACTORY).filter(experiment__user=user).exclude(experiment__status=Experiment.STATUS_DONE).exclude(experiment__status=Experiment.STATUS_DONE_WITH_ERRORS).exclude(experiment__status=Experiment.STATUS_FAILED)
#    if len(personalConfigurations) > 0:
#        raise Http404
#
#    tasks_db = FactoryTask.objects.all().order_by('taskNumber')
#    heuristic_versions = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True)
#
#    #Delete previous configurations (and experiments)
#    personalConfigurations = Configuration.objects.filter(experiment_type=Configuration.FACTORY).filter(experiment__user=user)
#    if len(personalConfigurations) > 0:
#        #remove datareports if any
#        #lock
#        filename = os.path.join(settings.DATA_REPORTS_ROOT, 'dataReports.lock')
#        lock_file = open(filename, 'wb')
#        try:
#            os.chmod(filename, 0766)
#        except:
#            pass
#        locks.lock(lock_file, locks.LOCK_EX)
#
#        #delete data report and above empty directory
#        for i in range(0,len(personalConfigurations)):
#            #check if dataReport exist
#            try:
#                dataReportFilename = personalConfigurations[i].experiment.data_report.filename
#                reportSplits = dataReportFilename.split("/")
#                fullReportDataPath = settings.DATA_REPORTS_ROOT+"/"+dataReportFilename
#                for j in reversed(range(0,len(reportSplits))):
#                    currentReportPos=""
#                    for k in range(0,j):
#                        currentReportPos = currentReportPos +"/"+reportSplits[k]
#
#
#                    possibleRemoveDir = settings.DATA_REPORTS_ROOT+currentReportPos
#                    if j == len(reportSplits)-1:
#                        os.remove("%s"%fullReportDataPath)
#                    if possibleRemoveDir == settings.DATA_REPORTS_ROOT:
#                        pass
#                    else:
#                        try:
#                            os.rmdir("%s"%possibleRemoveDir)
#                        except:
#                            pass
#            except:
#                #No data reports
#                pass
#        #unlock
#        lock_file.close()
#
#        personalConfigurations.delete()
#
#    try:
#        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)
#        debugging_entry.delete()
#    except:
#        pass
#
#    #Schedule experiments
#    for singleTask in tasks_db:
#        currentConfiguration = singleTask.config
#        experiments = Experiment.objects.filter(name=user.username.lower() + '/factory/task%d' % singleTask.taskNumber)
#
#        experiment = schedule_experiment(currentConfiguration, currentConfiguration.experiment_type,
#                                         user.username.lower() + '/factory/task%d' % singleTask.taskNumber,
#                                         user.username.lower() + '/factory/task%d' % singleTask.taskNumber,
#                                         currentConfiguration.heuristics,
#                                         heuristic_versions, [], [], singleTask.config.predictorName(),
#                                         user)
#
#        factoryTaskResult = FactoryTaskResult(task = singleTask, experiment = experiment)
#        factoryTaskResult.save()
#
#    return json_response(menu_status(user))


def test(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    #launch new experiments on tasks that are neither scheduled nor running

    tasks_db = []
    try:
        currentFactoryTaskResults = FactoryTaskResult.objects.filter(experiment__user=user)
    except:
        return json_response(menu_status(user))

    alltasks_db = FactoryTask.objects.all().order_by('taskNumber')

    #Check experience task that were never launched and add if any
    if len(currentFactoryTaskResults) < len(alltasks_db):
        for taskToAdd in alltasks_db:
            val = False
            innerCounter = 0
            for singleCurrentTask in currentFactoryTaskResults:
                innerCounter += 1
                if singleCurrentTask.task == taskToAdd:
                    val = True
                if val == True:
                    break
                if innerCounter == len(currentFactoryTaskResults):
                    if val == False:
                        tasks_db.append(taskToAdd)
            if innerCounter == 0:
                tasks_db.append(taskToAdd)

    #Schedule experiments for tasks that are not running or scheduled
    for singlefacttask_results in currentFactoryTaskResults:
        if (singlefacttask_results.experiment.status != Experiment.STATUS_SCHEDULED) and (singlefacttask_results.experiment.status != Experiment.STATUS_RUNNING):
            tasks_db.append(singlefacttask_results.task)

    tasks_db = sorted(tasks_db, key=lambda oneTask:oneTask.taskNumber)
    heuristic_versions = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True, checked=True)

    #Delete previous configurations (and experiments)
    personalConfigurations = Configuration.objects.filter(experiment_type=Configuration.FACTORY).filter(experiment__user=user).exclude(experiment__status=Experiment.STATUS_SCHEDULED).exclude(experiment__status=Experiment.STATUS_RUNNING)

    if len(personalConfigurations) > 0:
        #remove datareports if any
        #lock
        filename = os.path.join(settings.DATA_REPORTS_ROOT, 'dataReports.lock')
        lock_file = open(filename, 'wb')
        try:
            os.chmod(filename, 0766)
        except:
            pass
        locks.lock(lock_file, locks.LOCK_EX)

        #delete data report and above empty directory
        for i in range(0,len(personalConfigurations)):
            #check if dataReport exist
            try:
                dataReportFilename = personalConfigurations[i].experiment.data_report.filename
                reportSplits = dataReportFilename.split("/")
                fullReportDataPath = settings.DATA_REPORTS_ROOT+"/"+dataReportFilename
                for j in reversed(range(0,len(reportSplits))):
                    currentReportPos=""
                    for k in range(0,j):
                        currentReportPos = currentReportPos +"/"+reportSplits[k]


                    possibleRemoveDir = settings.DATA_REPORTS_ROOT+currentReportPos
                    if j == len(reportSplits)-1:
                        os.remove("%s"%fullReportDataPath)
                    if possibleRemoveDir == settings.DATA_REPORTS_ROOT:
                        pass
                    else:
                        try:
                            os.rmdir("%s"%possibleRemoveDir)
                        except:
                            pass
            except:
                #No data reports
                pass
        #unlock
        lock_file.close()

        personalConfigurations.delete()

    try:
        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)
        debugging_entry.delete()
    except:
        pass

    #Schedule experiments
    for singleTask in tasks_db:
        currentConfiguration = singleTask.config
        experiments = Experiment.objects.filter(name=user.username.lower() + '/factory/task%d' % singleTask.taskNumber)

        experiment = schedule_experiment(currentConfiguration, currentConfiguration.experiment_type,
                                         user.username.lower() + '/factory/task%d' % singleTask.taskNumber,
                                         user.username.lower() + '/factory/task%d' % singleTask.taskNumber,
                                         currentConfiguration.heuristics,
                                         heuristic_versions, [], [], singleTask.config.predictorName(),
                                         user)

        factoryTaskResult = FactoryTaskResult(task = singleTask, experiment = experiment)
        factoryTaskResult.save()

    return json_response(menu_status(user))


def retrieve_menu_status(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    return json_response(menu_status(user))


def test_results(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve all the tasks
    tasks = FactoryTask.objects.all().order_by('taskNumber')

    json_results = []

    for i in range(0, tasks.count()):
        json_results.append({ 'status': 'none' })

    hasHeuristics = False
    if not(user.is_anonymous()):
        # Retrieve the user's results
        task_results = FactoryTaskResult.objects.filter(experiment__user=user)

        hasHeuristics = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True, checked=True).count()>0

        for result in task_results:
            if result.experiment.status == Experiment.STATUS_SCHEDULED:
                json_results[result.task.taskNumber - 1]['status'] = 'scheduled'
            elif result.experiment.status == Experiment.STATUS_RUNNING:
                json_results[result.task.taskNumber - 1]['status'] = 'running'
            elif result.experiment.status == Experiment.STATUS_FAILED:
                json_results[result.task.taskNumber - 1]['status'] = 'failed'
            elif (result.experiment.status == Experiment.STATUS_DONE) or \
                 (result.experiment.status == Experiment.STATUS_DONE_WITH_ERRORS):
                if result.experiment.status == Experiment.STATUS_DONE:
                    json_results[result.task.taskNumber - 1]['status'] = 'done'
                else:
                    json_results[result.task.taskNumber - 1]['status'] = 'done_errors'

                json_results[result.task.taskNumber - 1]['obsolete'] = result.obsolete

                try:
                    gpresult = GoalPlanningResult.objects.get(experiment=result.experiment)
                    json_results[result.task.taskNumber - 1]['score'] = 0.01 * int((float(gpresult.nbActionsDone - gpresult.nbMimickingErrors) / gpresult.nbActionsDone) * 10000)
                except:
                    pass


    json_results = {
        'can_run_test' : hasHeuristics,
        'results': json_results,
        'menu_status': menu_status(user),
    }

    return json_response(json_results)

def test_results_tutorial(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    tutorial_step = (int(request.POST['tutorial_step']))
    # Retrieve all the tasks
    tasks = FactoryTask.objects.all().order_by('taskNumber')

    json_results = []

    for i in range(0, tasks.count()):
        json_results.append({ 'status': 'none' })

    hasHeuristics = True
    if not(user.is_anonymous()):
        # Retrieve the user's results
        task_results = FactoryTaskResult.objects.filter(experiment__user=user)
        for result in tasks:
            if tutorial_step == 0:
                json_results[result.taskNumber - 1]['status'] = 'scheduled'
            elif tutorial_step == 1:
                json_results[result.taskNumber - 1]['status'] = 'scheduled'
                if result.taskNumber == 1:
                    json_results[result.taskNumber - 1]['status'] = 'running'
            elif tutorial_step == 2:
                json_results[result.taskNumber - 1]['status'] = 'scheduled'
                if result.taskNumber == 1:
                    json_results[result.taskNumber - 1]['status'] = 'done'
                    json_results[result.taskNumber - 1]['score'] = 87.73
                if result.taskNumber == 2:
                    json_results[result.taskNumber - 1]['status'] = 'running'
            elif tutorial_step == 3:
                json_results[result.taskNumber - 1]['status'] = 'scheduled'
                if result.taskNumber == 1:
                    json_results[result.taskNumber - 1]['status'] = 'done'
                    json_results[result.taskNumber - 1]['score'] = 87.73
                if result.taskNumber == 2:
                    json_results[result.taskNumber - 1]['status'] = 'done'
                    json_results[result.taskNumber - 1]['score'] = 70.34
                if result.taskNumber == 3:
                    json_results[result.taskNumber - 1]['status'] = 'done'
                    json_results[result.taskNumber - 1]['score'] = 59.47

    json_results = {
        'can_run_test' : hasHeuristics,
        'results': json_results,
        'menu_status': menu_status(user),
    }

    return json_response(json_results)


def experiment_activity(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    total_anonUser = False
    test_button_available = False
    cookie_available = False
    cookie_value = ""
    if request.COOKIES.has_key('robot_uid'):
        cookie_value = request.COOKIES.__getitem__('robot_uid')
        cookie_available = True
    else :
        pass
    #get current user (anon or registered)
    user = request.user

    if user.is_anonymous():
        if cookie_available == True :
            #user is anonymous
            anonUser = "anon_%s"%cookie_value
            #check if anonymous user has already used the system
            try :
                #anonymous user find in database (similar to cookie)
                User.objects.all().get(username=anonUser)
            except User.DoesNotExist :
                #new anonymous user so create user
                new_anon_user = User.objects.create_user(anonUser,'','')
                new_anon_user.is_active = True
                new_anon_user.save()
            #anonymous user is refered by anon_<cookievalue>
            user = User.objects.all().get(username=anonUser)
        else :
            #user is anon with no cookie
            total_anonUser = True
    else :
        #user is known
        pass

    if total_anonUser == False :
        #check if user has heuristics
        personalConfigurations = Configuration.objects.filter(experiment_type=Configuration.FACTORY, experiment__user=user).exclude(experiment__status=Experiment.STATUS_DONE).exclude(experiment__status=Experiment.STATUS_DONE_WITH_ERRORS).exclude(experiment__status=Experiment.STATUS_FAILED)
        if len(personalConfigurations) > 0 :
            #experiences are running
            test_button_available = False
        else :
            #no experience launched
            test_button_available = True

    #send test button status
    if total_anonUser:
        return text_response('-')
    else:
        return text_response(test_button_available)


def singleTest(request, task_number):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    #if experiment is running,etc don't allow to go further
    total_anonUser = False
    test_button_available = False
    cookie_available = False
    cookie_value = ""
    if request.COOKIES.has_key('robot_uid'):
        cookie_value = request.COOKIES.__getitem__('robot_uid')
        cookie_available = True
    else :
        pass
    #get current user (anon or registered)
    user = request.user
    stringUserID = "%s"%user.id

    if stringUserID == "None":
        if cookie_available == True :
            #user is anonymous
            anonUser = "anon_%s"%cookie_value
            #check if anonymous user has already used the system
            try :
                #anonymous user find in database (similar to cookie)
                User.objects.all().get(username=anonUser)
            except User.DoesNotExist :
                #new anonymous user so create user
                new_anon_user = User.objects.create_user(anonUser,'','')
                new_anon_user.is_active = True
                new_anon_user.save()
            #anonymous user is refered by anon_<cookievalue>
            user = User.objects.all().get(username=anonUser)
        else :
            #user is anon with no cookie
            total_anonUser = True
    else :
        #user is known
        pass

    if total_anonUser:
        raise Http404

    #check if user has heuristics
    selectedTask = FactoryTask.objects.get(taskNumber=task_number)

    try:
        selectedTaskResult = FactoryTaskResult.objects.filter(experiment__user=user).get(task=selectedTask)
        personalConfigurations = Configuration.objects.filter(experiment_type=Configuration.FACTORY).filter(experiment__user=user).filter(experiment__id=selectedTaskResult.experiment.id).exclude(experiment__status=Experiment.STATUS_SCHEDULED).exclude(experiment__status=Experiment.STATUS_RUNNING).exclude(experiment__status=Experiment.STATUS_DELETED)

        if len(personalConfigurations) > 0 :
            #experiences are done

            #lock
            filename = os.path.join(settings.DATA_REPORTS_ROOT, 'dataReports.lock')
            lock_file = open(filename, 'wb')
            try:
                os.chmod(filename, 0766)
            except:
                pass
            locks.lock(lock_file, locks.LOCK_EX)

            #delete data report and above empty directory
            for i in range(0,len(personalConfigurations)):
                #check if dataReport exist
                try:
                    dataReportFilename = personalConfigurations[i].experiment.data_report.filename
                    reportSplits = dataReportFilename.split("/")
                    fullReportDataPath = settings.DATA_REPORTS_ROOT+"/"+dataReportFilename
                    for j in reversed(range(0,len(reportSplits))):
                        currentReportPos=""
                        for k in range(0,j):
                            currentReportPos = currentReportPos +"/"+reportSplits[k]


                        possibleRemoveDir = settings.DATA_REPORTS_ROOT+currentReportPos
                        if j == len(reportSplits)-1:
                            os.remove("%s"%fullReportDataPath)
                        if possibleRemoveDir == settings.DATA_REPORTS_ROOT:
                            pass
                        else:
                            try:
                                os.rmdir("%s"%possibleRemoveDir)
                            except:
                                pass
                except:
                    #No data reports
                    pass
            #unlock
            lock_file.close()

            personalConfigurations.delete()
    except:
        pass

    try:
        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user, task=selectedTask)
        debugging_entry.delete()
    except:
        pass

    # Schedule experiment
    heuristic_versions = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True, checked=True)
    currentConfiguration = selectedTask.config
    experiments = Experiment.objects.filter(name=user.username.lower() + '/factory/task%d' % selectedTask.taskNumber)

    experiment = schedule_experiment(currentConfiguration, currentConfiguration.experiment_type,
                                     user.username.lower() + '/factory/task%d' % selectedTask.taskNumber,
                                     user.username.lower() + '/factory/task%d' % selectedTask.taskNumber,
                                     currentConfiguration.heuristics,
                                     heuristic_versions, [], [], selectedTask.config.predictorName(),
                                     user)

    factoryTaskResult = FactoryTaskResult(task = selectedTask, experiment = experiment)
    factoryTaskResult.save()

    return json_response(menu_status(user))


def task_details(request, number):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)
    hasHeuristics = False
    if not(user.is_anonymous()):
        hasHeuristics = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True, checked=True).count()>0

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=number)
    except:
        raise Http404

    # Retrieve the results
    try:
        task_result = FactoryTaskResult.objects.get(experiment__user=user, task=task)
    except:
        task_result = None

    # Format the details
    details = {
        'description':      task.description,
        'image':            task.imageName,
        'status':           '-',
        'result':           None,
        'obsolete':         False,
        'instrument_views': [],
    }

    if task_result is not None:
        try:
            goalplanning_results = task_result.experiment.goalplanning_results.all()[0]

            details['result'] = {
                'nbActionsDone':     goalplanning_results.nbActionsDone,
                'nbMimickingErrors': goalplanning_results.nbMimickingErrors,
            }
        except:
            pass

        details['obsolete'] = task_result.obsolete

        if task_result.experiment.isDone():
            details['status'] = 'done'
        elif task_result.experiment.isScheduled():
            details['status'] = 'scheduled'
        elif task_result.experiment.isFailed():
            details['status'] = 'failed'
        else:
            details['status'] = 'running'

        try:
            for instrument in task_result.experiment.data_report.instruments_set.iterator():
                views = View.objects.filter(instrument=instrument, used_in_factory_results=True)
                for view in views:
                    details['instrument_views'].append(view.id)
        except:
            pass

    # Sends the response

    details['menu_status'] = menu_status(user)
    details['can_run_test'] = hasHeuristics

    return json_response(details)


def task_details_tutorial(request, number):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)
    hasHeuristics = False
    if not(user.is_anonymous()):
        hasHeuristics = HeuristicVersion.objects.filter(heuristic__author__id=user.id, heuristic__simple=True, checked=True).count()>0

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=number)
    except:
        raise Http404


    details = {"status": "done", "instrument_views": [8], "can_run_test": True,
    "description": task.description, 
    "image": task.imageName, "obsolete": False, "result":
    {"nbActionsDone": 13182, "nbMimickingErrors": 1617}, "menu_status":
    {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0,
    "compilation": 0, "recorded_data": 0, "experiments": 0,
    "heuristic_ids": {"in_progress": [], "errors": []},
    "heuristic_unchecked": 0}}

    

    return json_response(details)


def rounds_results(request, task_number):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    response_dict = {}

    try:
        task_result = FactoryTaskResult.objects.filter(experiment__user=user).get(task__taskNumber=task_number)
        result = task_result.experiment.goalplanning_results.all()[0]
        rounds = result.goalplanning_rounds.order_by('round')

        rounds_list = []
        for the_round in rounds:
            round_map = {
                'index':                   the_round.round,
                'result':                  the_round.result,
                'score':                   100.0 * float(the_round.nbActionsDone - the_round.nbMimickingErrors) / the_round.nbActionsDone,
                'nbActionsDone':           the_round.nbActionsDone,
                'nbMimickingErrors':       the_round.nbMimickingErrors,
                'nbNotRecommendedActions': the_round.nbNotRecommendedActions,
                'nbCorrectActions':        the_round.nbActionsDone - the_round.nbMimickingErrors,
            }

            rounds_list.append(round_map)

        rounds_list = sorted(rounds_list, cmp=lambda x, y: cmp(x['score'], y['score']))

        response_dict['rounds'] = rounds_list
    except:
        pass

    response_dict['menu_status'] = menu_status(user)

    return json_response(response_dict)

def rounds_results_tutorial(request, task_number):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    response_dict = {}
    response_dict = {"rounds": [{"index": 31, "nbMimickingErrors": 18, "nbCorrectActions": 20, "score": 52.631578947368418, "result": "R", "nbActionsDone": 38, "nbNotRecommendedActions": 0}, {"index": 94, "nbMimickingErrors": 36, "nbCorrectActions": 52, "score": 59.090909090909093, "result": "R", "nbActionsDone": 88, "nbNotRecommendedActions": 0}, {"index": 86, "nbMimickingErrors": 113, "nbCorrectActions": 172, "score": 60.350877192982459, "result": "R", "nbActionsDone": 285, "nbNotRecommendedActions": 0}, {"index": 96, "nbMimickingErrors": 23, "nbCorrectActions": 39, "score": 62.903225806451616, "result": "R", "nbActionsDone": 62, "nbNotRecommendedActions": 0}, {"index": 5, "nbMimickingErrors": 66, "nbCorrectActions": 125, "score": 65.445026178010465, "result": "R", "nbActionsDone": 191, "nbNotRecommendedActions": 0}, {"index": 82, "nbMimickingErrors": 36, "nbCorrectActions": 71, "score": 66.355140186915889, "result": "R", "nbActionsDone": 107, "nbNotRecommendedActions": 0}, {"index": 14, "nbMimickingErrors": 48, "nbCorrectActions": 102, "score": 68.0, "result": "R", "nbActionsDone": 150, "nbNotRecommendedActions": 0}, {"index": 7, "nbMimickingErrors": 9, "nbCorrectActions": 20, "score": 68.965517241379317, "result": "R", "nbActionsDone": 29, "nbNotRecommendedActions": 0}, {"index": 61, "nbMimickingErrors": 92, "nbCorrectActions": 207, "score": 69.230769230769226, "result": "R", "nbActionsDone": 299, "nbNotRecommendedActions": 0}, {"index": 79, "nbMimickingErrors": 47, "nbCorrectActions": 110, "score": 70.063694267515928, "result": "R", "nbActionsDone": 157, "nbNotRecommendedActions": 0}, {"index": 50, "nbMimickingErrors": 50, "nbCorrectActions": 122, "score": 70.930232558139537, "result": "R", "nbActionsDone": 172, "nbNotRecommendedActions": 0}, {"index": 28, "nbMimickingErrors": 27, "nbCorrectActions": 67, "score": 71.276595744680847, "result": "R", "nbActionsDone": 94, "nbNotRecommendedActions": 0}, {"index": 41, "nbMimickingErrors": 27, "nbCorrectActions": 67, "score": 71.276595744680847, "result": "R", "nbActionsDone": 94, "nbNotRecommendedActions": 0}, {"index": 33, "nbMimickingErrors": 24, "nbCorrectActions": 68, "score": 73.913043478260875, "result": "R", "nbActionsDone": 92, "nbNotRecommendedActions": 0}, {"index": 62, "nbMimickingErrors": 23, "nbCorrectActions": 72, "score": 75.78947368421052, "result": "R", "nbActionsDone": 95, "nbNotRecommendedActions": 0}, {"index": 85, "nbMimickingErrors": 34, "nbCorrectActions": 108, "score": 76.056338028169009, "result": "R", "nbActionsDone": 142, "nbNotRecommendedActions": 0}], "menu_status": {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": 0, "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}}
    return json_response(response_dict)



def sequence_details(request, task, sequence):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=task)
    except:
        raise Http404

    # Retrieve the results
    try:
        task_result = FactoryTaskResult.objects.get(experiment__user=user, task=task)
    except:
        raise Http404

    if not(task_result.experiment.isDone()):
        raise Http404

    # Format the details
    details = {
        'description': task.description,
        'obsolete':    task_result.obsolete,
        'result':      None,
    }

    try:
        goalplanning_results = task_result.experiment.goalplanning_results.all()[0]
        goalplanning_round = goalplanning_results.goalplanning_rounds.get(round=sequence)

        details['result'] = {
            'nbActionsDone':     goalplanning_round.nbActionsDone,
            'nbMimickingErrors': goalplanning_round.nbMimickingErrors,
        }
    except:
        raise Http404

    details['menu_status'] = menu_status(user)

    # Sends the response
    return json_response(details)

def sequence_details_tutorial(request, task, sequence):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)
    details = {}
    details = {"result": {"nbActionsDone": 285, "nbMimickingErrors": 113}, "description": "Reach a red flag in a rectangular room", "menu_status": {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": None, "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}, "obsolete": False}


    # Sends the response
    return json_response(details)



def recorded_data(request, task, sequence, frame_index):

    def _fill_buffer(data_file, buffer, offset, size, target_size=None):
        if len(buffer) - offset < size:
            buffer = buffer[offset:]

            if target_size is None:
                target_size = size
            else:
                target_size = max(size, target_size)

            buffer += data_file.read(target_size - len(buffer))
            offset = 0

        return (buffer, offset)


    def _next_frame(data_file, buffer, offset, store=True):
        (buffer, offset) = _fill_buffer(data_file, buffer, offset, 1024 * 1024 * 1024)

        frame = {
            'limit_reached': False,
        }

        # FRAME <index>
        stop_offset = buffer.find('\n', offset)
        if stop_offset == -1:
            return (None, None, None)

        line = buffer[offset:stop_offset]
        if not(line.startswith('FRAME ')):
            return (None, None, None)

        frame['index'] = int(line[6:])

        offset = stop_offset + 1

        # SRC_IMAGE <width>x<height> <binary data>
        stop_offset = buffer.find(' ', offset)
        if stop_offset == -1:
            return (None, None, None)

        tag = buffer[offset:stop_offset]
        if tag != 'SRC_IMAGE':
            return (None, None, None)

        offset = stop_offset + 1

        stop_offset = buffer.find(' ', offset)
        if stop_offset == -1:
            return (None, None, None)

        size = buffer[offset:stop_offset]
        dim = map(lambda x: int(x), size.split('x'))
        if len(dim) != 2:
            return (None, None, None)

        offset = stop_offset + 1

        (buffer, offset) = _fill_buffer(data_file, buffer, offset, dim[0] * dim[1] * 3)

        if len(buffer) - offset < dim[0] * dim[1] * 3:
            return (None, None, None)

        stop_offset = offset + dim[0] * dim[1] * 3

        if store:
            frame['src_image'] = {
                'width': dim[0],
                'height': dim[1],
                'pixels': base64.encodestring(buffer[offset:stop_offset]),
            }

        offset = stop_offset

        # User-dependent tags
        (buffer, offset) = _fill_buffer(data_file, buffer, offset, 1024 * 1024 * 1024)

        frame['user_data'] = []

        while True:
            (buffer, offset) = _fill_buffer(data_file, buffer, offset, 512 * 1024 * 1024, 1024 * 1024 * 1024)

            stop_offset1 = buffer.find(' ', offset, offset + 14)
            stop_offset2 = buffer.find('\n', offset, offset + 14)

            if (stop_offset1 == -1) and (stop_offset2 == -1):
                return (None, None, None)
            elif (stop_offset1 != -1) and (stop_offset2 != -1):
                stop_offset = min(stop_offset1, stop_offset2)
            else:
                stop_offset = max(stop_offset1, stop_offset2)

            tag = buffer[offset:stop_offset]
            offset = stop_offset + 1

            # TEXT <size> <text>
            if tag == 'TEXT':
                stop_offset = buffer.find(' ', offset)
                size = int(buffer[offset:stop_offset])

                offset = stop_offset + 1

                (buffer, offset) = _fill_buffer(data_file, buffer, offset, size, 1024 * 1024 * 1024)

                if len(buffer) - offset < size:
                    return (None, None, None)

                stop_offset = offset + size

                if store:
                    frame['user_data'].append({
                        'type': 'text',
                        'text': buffer[offset:stop_offset],
                    })

                offset = stop_offset

            # IMAGERGB <width>x<height> <binary data>
            elif tag == 'IMAGERGB':
                stop_offset = buffer.find(' ', offset)
                if stop_offset == -1:
                    return (None, None, None)

                size = buffer[offset:stop_offset]
                dim = map(lambda x: int(x), size.split('x'))
                if len(dim) != 2:
                    return (None, None, None)

                offset = stop_offset + 1

                (buffer, offset) = _fill_buffer(data_file, buffer, offset, dim[0] * dim[1] * 3)

                if len(buffer) - offset < dim[0] * dim[1] * 3:
                    return (None, None, None)

                stop_offset = offset + dim[0] * dim[1] * 3

                if store:
                    frame['user_data'].append({
                        'type': 'rgb',
                        'width': dim[0],
                        'height': dim[1],
                        'pixels': base64.encodestring(buffer[offset:stop_offset]),
                    })

                offset = stop_offset

            # IMAGEGRAY <width>x<height> <binary data>
            elif tag == 'IMAGEGRAY':
                stop_offset = buffer.find(' ', offset)
                if stop_offset == -1:
                    return (None, None, None)

                size = buffer[offset:stop_offset]
                dim = map(lambda x: int(x), size.split('x'))
                if len(dim) != 2:
                    return (None, None, None)

                offset = stop_offset + 1

                (buffer, offset) = _fill_buffer(data_file, buffer, offset, dim[0] * dim[1])

                if len(buffer) - offset < dim[0] * dim[1]:
                    return (None, None, None)

                stop_offset = offset + dim[0] * dim[1]

                if store:
                    frame['user_data'].append({
                        'type': 'gray',
                        'width': dim[0],
                        'height': dim[1],
                        'pixels': base64.encodestring(buffer[offset:stop_offset]),
                    })

                offset = stop_offset

            # LIMIT_REACHED
            elif tag == 'LIMIT_REACHED':
                frame['limit_reached'] = True

            # END_FRAME
            elif tag == 'END_FRAME':
                return (buffer, offset, frame)


    must_return_actions = False
    if request.POST.has_key('actions'):
         must_return_actions = (int(request.POST['actions']) == 1)

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=task)
    except:
        raise Http404

    # Retrieve the results
    try:
        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)

        if (debugging_entry.task != task) or (debugging_entry.sequence != int(sequence)):
            if (debugging_entry.status == DebuggingEntry.STATUS_SCHEDULED) or \
               (debugging_entry.status == DebuggingEntry.STATUS_RUNNING):
                return json_response( { 'status': 'other', 'task': debugging_entry.task.taskNumber, 'sequence': int(debugging_entry.sequence), 'menu_status': menu_status(user) } )
            else:
                return json_response( { 'status': 'none', 'menu_status': menu_status(user) } )
    except:
        return json_response( { 'status': 'none', 'menu_status': menu_status(user) } )

    # Prepare the JSON response
    response = {
        'heuristic_version_id': debugging_entry.heuristic_version.id,
        'heuristic_name':       debugging_entry.heuristic_version.heuristic.name,
        'start_frame':          debugging_entry.start_frame,
        'end_frame':            debugging_entry.end_frame,
        'obsolete':             debugging_entry.obsolete,
        'frames':               [],
    }

    # Is it still running?
    if debugging_entry.status == DebuggingEntry.STATUS_SCHEDULED:
        response['status'] = 'scheduled'

    elif debugging_entry.status == DebuggingEntry.STATUS_RUNNING:
        response['status'] = 'running'

    # Was there an error?
    elif debugging_entry.status == DebuggingEntry.STATUS_FAILED:
        response['status'] = 'error'
        response['error'] = debugging_entry.error_details

    # Done
    else:
        response['status'] = 'done'

        # Open the file
        data_file = open(os.path.join(settings.HEURISTICS_DEBUGGING_ROOT, debugging_entry.filename()), "rb")

        buffer = ''
        offset = 0
        json_frame = None

        if request.POST.has_key('clue'):
            clue = int(request.POST['clue'])

            data_file.seek(clue, os.SEEK_SET)

            (buffer, offset, json_frame) = _next_frame(data_file, buffer, offset)
            if (json_frame is None) or (json_frame['index'] != int(frame_index)):
                data_file.seek(0, os.SEEK_SET)
                buffer = ''
                offset = 0
                json_frame = None

        # Skip frames
        if json_frame is None:
            for i in range(0, int(frame_index)):
                (buffer, offset, json_frame) = _next_frame(data_file, buffer, offset, False)
                if json_frame is None:
                    raise Http404

            # Retrieve the frame requested by the client
            (buffer, offset, json_frame) = _next_frame(data_file, buffer, offset)
            if json_frame is None:
                raise Http404

        response['frames'].append(json_frame)

        response['eof'] = json_frame['limit_reached'] or ((len(buffer) == offset) and (len(data_file.read(1)) == 0))
        response['clue'] = data_file.tell() - len(buffer) + offset

        try:
            if must_return_actions:
                task_result = FactoryTaskResult.objects.get(task=task, experiment__user=user)

                if (task_result.experiment.data_report.instruments_set.filter(author__username='MASH', name='actions').count() == 1):
                    # Setup the locking mechanism
                    filename = os.path.join(settings.SNIPPETS_ROOT, 'snippets.lock')
                    lock_file = open(filename, 'wb')
                    try:
                        os.chmod(filename, 0766)
                    except:
                        pass
                    locks.lock(lock_file, locks.LOCK_EX)

                    # Uncompress the file we are interested in from the report
                    tar = tarfile.open(os.path.join(settings.DATA_REPORTS_ROOT, task_result.experiment.data_report.filename), 'r:gz')
                    actions_file = tar.extractfile(tar.getmember('mash/actions.data'))
                    content = actions_file.read()
                    tar.close()

                    locks.unlock(lock_file)

                    while content[0] == '#':
                        start = content.find('\n')
                        content = content[start+1:]

                    start = content.find('SEQUENCE %d\n' % debugging_entry.sequence)
                    end = content.find('SEQUENCE_END\n', start)

                    lines = content[start:end].split('\n')[1:-1]

                    response['actions'] = map(lambda x: map(lambda y: int(y), x.split(' ')[2:]), lines)
        except:
            pass


    # Sends the response
    response['menu_status'] = menu_status(user)

    return json_response(response)


def recorded_data_tutorial(request, task, sequence, frame_index):
    tutorial_step = 0
    output = {}

    if request.POST.has_key('tutorial'):
            tutorial_step = int(request.POST['tutorial'])

    print tutorial_step
    if tutorial_step == -1:
        output = {"status": "none", "menu_status": {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": None, "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}}
        print "inside"

    if tutorial_step == 0:
        output = {"status": "none", "start_frame": -1, "end_frame": -1, "obsolete": False, "actions": [[0, 0], [3, 0], [0, 0], [0, 0]], "heuristic_version_id": 824, "menu_status": {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": "running", "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}, "frames": [], "heuristic_name": "center_red"}
    if tutorial_step == 1:
        output = {"status": "running", "start_frame": -1, "end_frame": -1, "obsolete": False, "heuristic_version_id": 824, "menu_status": {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": "running", "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}, "frames": [], "heuristic_name": "center_red"}
    if tutorial_step == 2:
        inputSourceFile = open(os.path.join(settings.MEDIA_ROOT, 'tutorial_frame_0.txt'), 'rb')
        output = inputSourceFile.read()
        inputSourceFile.close()
    if tutorial_step == 3:
        inputSourceFile = open(os.path.join(settings.MEDIA_ROOT, 'tutorial_frame_1.txt'), 'rb')
        output = inputSourceFile.read()
        inputSourceFile.close()
    if tutorial_step == 4:
        inputSourceFile = open(os.path.join(settings.MEDIA_ROOT, 'tutorial_frame_2.txt'), 'rb')
        output = inputSourceFile.read()
        inputSourceFile.close()
    if tutorial_step == 5:
        inputSourceFile = open(os.path.join(settings.MEDIA_ROOT, 'tutorial_frame_3.txt'), 'rb')
        output = inputSourceFile.read()
        inputSourceFile.close()

    # Sends the response
    return json_response(output)
   


def record_data(request, task, sequence, heuristic):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Delete the existing debugging entry for this user (if any)
    debugging_entry = None
    try:
        debugging_entry = DebuggingEntry.objects.get(heuristic_version__heuristic__author=user)

        # It should not be possible to invoke this view if a debugging session is already scheduled/running
        if (debugging_entry.status == DebuggingEntry.STATUS_DONE) or \
           (debugging_entry.status == DebuggingEntry.STATUS_ERROR):
           filename = os.path.join(settings.HEURISTICS_DEBUGGING_ROOT, debugging_entry.filename())
           debugging_entry.delete()
           debugging_entry = None
           os.remove(filename)
    except:
        pass

    if debugging_entry is not None:
        raise Http404

    # Create a new debugging entry
    try:
        debugging_entry                   = DebuggingEntry()
        debugging_entry.task              = FactoryTask.objects.get(taskNumber=int(task))
        debugging_entry.sequence          = int(sequence)
        debugging_entry.heuristic_version = HeuristicVersion.objects.get(id=int(heuristic))
        debugging_entry.status            = DebuggingEntry.STATUS_SCHEDULED
        debugging_entry.save()
    except:
        raise Http404

    # Tell the Scheduler about the new debugging session
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand(Message('DEBUG_HEURISTIC', [debugging_entry.id]))
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)

    # Sends a response to the client
    return json_response(menu_status(user))

def record_data_tutorial(request, task, sequence, heuristic):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)
    
    tutorial_step = (int(request.POST['tutorial_step']))

    # Sends a response to the client
    output = {}
    if tutorial_step == -1 :
        output = {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": 0, "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}
    if tutorial_step == 0 :
        output = {"nb_total_numbers_heuristics": 2, "nb_compilation_errors": 0, "compilation": 0, "recorded_data": "running", "experiments": 0, "heuristic_ids": {"in_progress": [], "errors": []}, "heuristic_unchecked": 0}

    return json_response(output)


def snippet(request, task, instrument_view):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=task)
    except:
        raise Http404

    # Retrieve the instrument view
    try:
        instrument_view = View.objects.get(id=instrument_view)
    except:
        raise Http404

    if not(instrument_view.used_in_factory_results):
        raise Http404

    # Retrieve the results
    try:
        task_result = FactoryTaskResult.objects.get(experiment__user=user, task=task)
    except:
        raise Http404

    snippet = get_or_create_snippet(task_result.experiment.data_report, instrument_view)

    # Sends the response
    return text_response(html_snippet(request, snippet.id).content)

def snippet_tutorial(request, task, instrument_view):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve the task
    try:
        task = FactoryTask.objects.get(taskNumber=task)
    except:
        raise Http404

    text = "<table><tbody><tr><td><span>tutorial_center_red</span></td><td class=\"number\">1</td><td class=\"total\">/1</td></tr><tr><td><span>tutorial_dummy</span></td><td class=\"number\">1</td><td class=\"total\">/1</td></tr></tbody></table>"
    # Sends the response
    return text_response(text)

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
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import defaultfilters
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.models import HeuristicEvaluationResults
from mash.heuristics.models import HeuristicEvaluationStep
from mash.heuristics.forms import UploadHeuristicForm, HeuristicDetailsForm
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
from mash.clustering.models import SignatureStatus
from mash.factory.views import process_cookie
from pymash.gitrepository import GitRepository
from pymash.messages import Message
from mash.heuristics.utilities import *
from contests.views import enter_contest
from contests.models import ContestEntry
from phpbb.utilities import createTopic
from tools.views import get_error_report_as_html
from tools.models import PluginErrorReport
from servers import acquireExperimentsScheduler, releaseExperimentsScheduler
from datetime import datetime, date, timedelta
from math import sqrt
import utils.mediawiki as mediawiki
import os
import difflib
import xml.dom.minidom


#---------------------------------------------------------------------------------------------------
# Display a heuristic
#---------------------------------------------------------------------------------------------------
def heuristic(request, heuristic_id=None, version_id=None):

    # Initialisations
    version             = None
    heuristic           = None
    display_upload_box  = False
    html_error_reports  = None
    html_versions_list  = None
    html_derived_list   = None
    html_source_code    = None

    # Retrieve the heuristic
    if version_id is not None:
        version = get_object_or_404(HeuristicVersion, pk=version_id)
        heuristic = version.heuristic
    else:
        heuristic = get_object_or_404(Heuristic, pk=heuristic_id)
        if (request.user == heuristic.author) or request.user.is_superuser:
            version = heuristic.latest_version()
        else:
            version = heuristic.latest_public_version

    # Check that the user has the right to see the heuristic
    public_only = (request.user != heuristic.author) and not(request.user.is_superuser)
    if not(version) or (public_only and not(version.public)):
        raise Http404

    if request.GET.has_key('upload'):
        try:
            display_upload_box = (int(request.GET['upload']) != 0)
        except:
            pass


    # Render the error reports
    if version.error_reports is not None:
        html_error_reports = ''
        for report in version.error_reports.iterator():
            html_error_reports += get_error_report_as_html(report, request.user, display_experiment=True)


    # Preprocess the list of heuristics to display
    versions_mode           = None
    derived_mode            = None
    versions_configuration  = None
    derived_configuration   = None
    versions_params         = ''
    derived_params          = ''

    if not(public_only):
        if heuristic.versions_count() > 1:
            versions_mode = MODES[MODE_OWN_HEURISTIC_VERSIONS]

        if heuristic.derived_heuristics_count() >= 1:
            derived_mode = MODES[MODE_ALL_DERIVED_HEURISTICS]
    else:
        if heuristic.public_versions_count() > 1:
            versions_mode = MODES[MODE_PUBLIC_HEURISTIC_VERSIONS]

        if heuristic.public_derived_heuristics_count() >= 1:
            derived_mode = MODES[MODE_PUBLIC_DERIVED_HEURISTICS]

    if versions_mode is not None:
        versions_configuration = ListConfiguration(versions_mode, request, heuristic=heuristic,
                                                   heuristic_version=version,
                                                   heuristics_link=HEURISTICS_LINK_VERSIONS,
                                                   url_args_prefix='v')
        versions_configuration.url = ''
        versions_params = versions_configuration.fullUrl()[1:]

    if derived_mode is not None:
        derived_configuration = ListConfiguration(derived_mode, request, heuristic=heuristic,
                                                  heuristics_link=HEURISTICS_LINK_MODIFICATION,
                                                  url_args_prefix='d')
        derived_configuration.url = ''
        derived_params = derived_configuration.fullUrl()[1:]

    if versions_mode is not None:
        versions_configuration.url = request.path
        if len(derived_params) > 0:
            versions_configuration.url += '?%s' % derived_params

    if derived_mode is not None:
        derived_configuration.url = request.path
        if len(versions_params) > 0:
            derived_configuration.url += '?%s' % versions_params


    # Render the list of the other versions
    if versions_configuration is not None:
        renderer = ListRenderer(versions_mode, versions_configuration)
        html_versions_list = renderer.render(request)

    # Render the list of the derived heuristics
    if derived_configuration is not None:
        renderer = ListRenderer(derived_mode, derived_configuration)
        html_derived_list = renderer.render(request)

    # Retrieve the source code
    if version.status != HeuristicVersion.STATUS_DELETED:
        if not(public_only) or not(version.public) or version.is_visible():
            html_source_code = get_source_code_as_html(version)
        else:
            html_source_code = '<p class="explanation">The source code of this heuristic will not be publicly available until the %s.</p>' % version.opensource_date.strftime('%B %d, %Y')
    else:
        html_source_code = '<p class="explanation">This heuristic version has been deleted. The source code isn\'t available anymore.</p>'

    # Parse the mediawiki-style heuristic description
    if len(heuristic.description.strip()) > 0:
        description = mediawiki.parse(heuristic.description.strip(), showToc=False)
    else:
        description = None

    # Retrieves the additional texts that might be needed
    text_upload_confirmation        = None
    text_publication_confirmation   = None
    text_deletion_confirmation      = None

    text_upload_confirmation    = Text.getContent('HEURISTIC_UPLOAD_CONFIRMATION')
    text_upload_choice          = Text.getContent('HEURISTIC_UPLOAD_CHOICE')

    if not(version.public):
        text_publication_confirmation = Text.getContent('HEURISTIC_PUBLICATION_CONFIRMATION')

        delta = timedelta(7)
        publication_date = date.today()
        for i in range(1, 5):
            publication_date = publication_date + delta
            text_publication_confirmation = text_publication_confirmation.replace('$DATE%d' % i, '%s' % publication_date.strftime('%B %d, %Y'))

        if heuristic.versions_count() == 1:
            text_deletion_confirmation = Text.getContent('HEURISTIC_DELETION_CONFIRMATION')
        else:
            text_deletion_confirmation = Text.getContent('HEURISTIC_VERSION_DELETION_CONFIRMATION')


    # Create a fake mode to please the templates
    mode = Mode()
    mode.can_display_tools = not(public_only)
    mode.can_upload = not(public_only)

    # Retrieve the signature of the heuristic
    try:
        signature_status = SignatureStatus.objects.get(signature__heuristic_version=version, algorithm__name='rvcluster')
    except:
        signature_status = None

    # Rendering
    return render_to_response('heuristics/heuristic.html',
                              {'heuristic': heuristic,
                               'version': version,
                               'signature_status': signature_status,
                               'author_profile': heuristic.author.get_profile(),
                               'description': description,
                               'html_error_reports': html_error_reports,
                               'html_versions_list': html_versions_list,
                               'html_derived_list': html_derived_list,
                               'html_source_code': html_source_code,
                               'phases': HeuristicTestStatus.PHASES,
                               'mode': mode,
                               'nb_heuristics_per_page': NB_HEURISTICS_PER_PAGE,
                               'display_upload_box': display_upload_box,
                               'text_upload_confirmation': text_upload_confirmation,
                               'text_upload_choice': text_upload_choice,
                               'text_publication_confirmation': text_publication_confirmation,
                               'text_deletion_confirmation': text_deletion_confirmation,
                               'can_see_check_box': not(public_only),
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display a heuristic (referenced by its name)
#---------------------------------------------------------------------------------------------------
def heuristic_by_name(request, author_name, heuristic_name, version=None):

    try:
        # Retrieve the heuristic
        if version is not None:
            heuristic_version = HeuristicVersion.objects.filter(heuristic__author__username=author_name,
                                                                heuristic__name=heuristic_name,
                                                                version=version)
            return heuristic(request, version_id=heuristic_version[0].id)
        else:
            heuristic_instance = Heuristic.objects.filter(author__username=author_name,
                                                          name=heuristic_name)
            return heuristic(request, heuristic_id=heuristic_instance[0].id)
    except:
        raise Http404


#---------------------------------------------------------------------------------------------------
# Display the list of all the public heuristics (eventually sorted and filtered)
#---------------------------------------------------------------------------------------------------
def heuristics_list(request):

    mode = MODES[MODE_ALL_PUBLIC_HEURISTICS]
    configuration = ListConfiguration(mode, request)
    renderer = ListRenderer(mode, configuration)

    html_list = renderer.render(request)

    # Retrieves the additional texts that might be needed
    text_upload_confirmation = Text.getContent('HEURISTIC_UPLOAD_CONFIRMATION')
    text_upload_choice = Text.getContent('HEURISTIC_UPLOAD_CHOICE')

    # Render the page
    return render_to_response('heuristics/list.html',
                              {'mode': mode,
                               'html_list': html_list,
                               'nb_heuristics_per_page': NB_HEURISTICS_PER_PAGE,
                               'text_upload_confirmation': text_upload_confirmation,
                               'text_upload_choice': text_upload_choice,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display the list of the public heuristics of a specific user (eventually sorted and filtered)
#---------------------------------------------------------------------------------------------------
def public_heuristics_list(request, user_id=None):

    if user_id is not None:
        mode = MODES[MODE_USER_PUBLIC_HEURISTICS]
        user = get_object_or_404(User, id=user_id)
    elif request.user.is_anonymous():
        return HttpResponseRedirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
    else:
        mode = MODES[MODE_OWN_PUBLIC_HEURISTICS]
        user = request.user

    configuration = ListConfiguration(mode, request, user=user)
    renderer = ListRenderer(mode, configuration)

    html_list = renderer.render(request)

    # Retrieves the additional texts that might be needed
    text_upload_confirmation = Text.getContent('HEURISTIC_UPLOAD_CONFIRMATION')
    text_upload_choice = Text.getContent('HEURISTIC_UPLOAD_CHOICE')

    # Render the page
    return render_to_response('heuristics/list.html',
                              {'mode': mode,
                               'html_list': html_list,
                               'nb_heuristics_per_page': NB_HEURISTICS_PER_PAGE,
                               'text_upload_confirmation': text_upload_confirmation,
                               'text_upload_choice': text_upload_choice,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display the list of the private heuristics of a specific user (eventually sorted and filtered)
# Only available to the owner of those heuristics and to the staff
#---------------------------------------------------------------------------------------------------
@login_required
def private_heuristics_list(request, user_id=None):

    if (user_id is not None) and (request.user.id != int(user_id)):
        if not request.user.is_superuser:
            return HttpResponseForbidden
        mode = MODES[MODE_USER_PRIVATE_HEURISTICS]
        user = User.objects.get(id=user_id)
    else:
        mode = MODES[MODE_OWN_PRIVATE_HEURISTICS]
        user = request.user

    configuration = ListConfiguration(mode, request, user=user)
    renderer = ListRenderer(mode, configuration)

    html_list = renderer.render(request)

    # Retrieves the additional texts that might be needed
    text_upload_confirmation = Text.getContent('HEURISTIC_UPLOAD_CONFIRMATION')
    text_upload_choice = Text.getContent('HEURISTIC_UPLOAD_CHOICE')

    # Render the page
    return render_to_response('heuristics/list.html',
                              {'mode': mode,
                               'html_list': html_list,
                               'nb_heuristics_per_page': NB_HEURISTICS_PER_PAGE,
                               'text_upload_confirmation': text_upload_confirmation,
                               'text_upload_choice': text_upload_choice,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display the popup list allowing to select one heuristic (eventually sorted and filtered)
#---------------------------------------------------------------------------------------------------
def search_popup(request, only_own=False):

    if only_own:
        mode = MODES[MODE_SELECT_OWN_HEURISTIC]
        user = request.user
    else:
        mode = MODES[MODE_SELECT_HEURISTIC]
        user = None

    configuration = ListConfiguration(mode, request, user=user, search_popup=True)
    renderer = ListRenderer(mode, configuration)

    html_list = renderer.render(request)

    # Render the page
    return render_to_response('heuristics/search_popup.html',
                              {'html_list': html_list,
                               'nb_heuristics_per_page': NB_HEURISTICS_PER_PAGE,
                               'search_popup': True,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Handle the upload of a new heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def upload(request):

    # Check that a formular was posted
    if not(request.method == 'POST'):
        return HttpResponseRedirect('/heuristics/')

    # Process the form
    form = UploadHeuristicForm(request.POST, request.FILES)
    if form.is_valid():

        # Retrieve the file
        heuristic_file = request.FILES['heuristic_file']

        # Retrieve the upload repository and lock it
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        repo.lock()

        try:
            # Create it if necessary
            repo.createIfNotExists()

            # Check that the heuristic name is free (we assume that the user wants to create a new heuristic)
            (heuristic_name, extension) = os.path.splitext(heuristic_file.name)
            name = defaultfilters.slugify(heuristic_name.strip().replace(' ', '').replace('-', '_'))

            i = 1
            while (Heuristic.objects.filter(author__id=request.user.id).filter(name=name).count() > 0):
                i += 1
                name = '%s%d' % (heuristic_name, i)

            heuristic_name = name
            heuristic_file_name = '%s%s' % (heuristic_name, extension)

            # Create the user directory in the upload repository if necessary
            user_path = os.path.join(repo.fullpath(), request.user.username.lower())
            if not(os.path.exists(user_path)):
                os.mkdir(user_path)

            # Write the file into the upload repository
            destination = open(os.path.join(user_path, heuristic_file_name), 'w')
            for chunk in heuristic_file.chunks():
                destination.write(chunk)
            destination.close()

            # Commit the new file
            repo.commitFile('%s/%s' % (request.user.username.lower(), heuristic_file_name),
                            "'%s' uploaded heuristic '%s'" % (request.user.username, heuristic_file_name),
                            settings.COMMIT_AUTHOR)

            # Retrieve the git ID of the file
            blob = repo.repository().tree()[request.user.username.lower()][heuristic_file_name]


            # Add informations about the heuristic in the database
            heuristic           = Heuristic()
            heuristic.author    = request.user
            heuristic.name      = heuristic_name
            heuristic.save()

            version             = HeuristicVersion()
            version.heuristic   = heuristic
            version.filename    = heuristic_file_name
            version.upload_date = datetime.now()
            version.save()

            test_status                     = HeuristicTestStatus()
            test_status.heuristic_version   = version
            test_status.phase               = HeuristicTestStatus.PHASE_STATUS
            test_status.save()

            # Release the lock
            repo.unlock()

            # Tell the experiments scheduler about the new heuristic
            scheduler = acquireExperimentsScheduler()
            if scheduler is not None:
                scheduler.sendCommand(Message('CHECK_HEURISTIC', [version.id]))
                scheduler.waitResponse()
                releaseExperimentsScheduler(scheduler)

            return HttpResponseRedirect('/heuristics/v%d/' % version.id)

        except:
            repo.unlock()
            raise

#---------------------------------------------------------------------------------------------------
# Handle the upload of a new version of a heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def upload_version(request, heuristic_id):

    # Check that a formular was posted
    if not(request.method == 'POST'):
        return HttpResponseRedirect('/heuristics/')

    # Retrieve the heuristic
    heuristic_id = int(heuristic_id)
    heuristic = get_object_or_404(Heuristic, pk=heuristic_id)

    # Check that the user has the right to modify it
    if (heuristic.author != request.user) and not(request.user.is_superuser):
        raise Http404

    # Process the form
    form = UploadHeuristicForm(request.POST, request.FILES)
    if form.is_valid():

        # Retrieve the file
        heuristic_file = request.FILES['heuristic_file']

        # Retrieve the upload repository and lock it
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        repo.lock()

        try:
            # Create it if necessary
            repo.createIfNotExists()

            # Test if another version of the heuristic wasn't checked (or didn't pass the check)
            if (heuristic.latest_private_version is None) or heuristic.latest_private_version.evaluated or \
               (heuristic.latest_private_version.version < heuristic.latest_version().version):
                version             = HeuristicVersion()
                version.heuristic   = heuristic

                if heuristic.latest_version() is not None:
                    version.version = heuristic.latest_version().version + 1
                else:
                    version.version = heuristic.latest_checked_version().version + 1

            else:
                version = heuristic.latest_private_version

                # Retrieve the repository containing the file
                if version.checked:
                    repo2 = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                else:
                    repo2 = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
                repo2.lock()

                # Ensure that the content of the file is different
                blob = repo2.repository().tree()[version.heuristic.author.username.lower()][version.filename]
                if len(blob.data) == heuristic_file.size:
                    offset = 0
                    no_diff = True
                    for chunk in heuristic_file.chunks():
                        if hash(blob.data[offset:offset+len(chunk)]) != hash(chunk):
                            no_diff = False
                            break

                    if no_diff:
                        repo.unlock()
                        return HttpResponseRedirect('/heuristics/v%d/' % version.id)

                # Remove the error reports (if any)
                if version.error_reports.count() > 0:
                    version.error_reports.all().delete()

                # Cancel the evaluation experiments still running
                scheduler = acquireExperimentsScheduler()
                if scheduler is not None:
                    for evaluation_results in version.evaluation_results.exclude(experiment__status=Experiment.STATUS_DONE):
                        scheduler.sendCommand(Message('CANCEL_EXPERIMENT', [evaluation_results.experiment.id]))
                        scheduler.waitResponse()
                    releaseExperimentsScheduler(scheduler)

                # Remove the file from the repository
                try:
                    repo2.removeFile('%s/%s' % (request.user.username.lower(), version.filename),
                                     "Heuristic '%s' deleted (by %s), will be replaced by another version" % (version.fullname(), request.user.username),
                                     settings.COMMIT_AUTHOR)
                except:
                    pass
                repo2.unlock()

            # Add informations about the version
            if version.version > 1:
                version.filename = '%s_v%d.cpp' % (heuristic.name, version.version)
            else:
                version.filename = '%s.cpp' % heuristic.name

            version.upload_date = datetime.now()
            version.checked = False

            # Create the user directory in the upload repository if necessary
            user_path = os.path.join(repo.fullpath(), request.user.username.lower())
            if not(os.path.exists(user_path)):
                os.mkdir(user_path)

            # Write the file into the upload repository
            destination = open(os.path.join(user_path, version.filename), 'w')
            for chunk in heuristic_file.chunks():
                destination.write(chunk)
            destination.close()

            # Commit the new file
            repo.commitFile('%s/%s' % (request.user.username.lower(), version.filename),
                            "'%s' uploaded new version of heuristic '%s'" % (request.user.username, heuristic.name),
                            settings.COMMIT_AUTHOR)

            # Save the version in the database
            version.save()

            try:
                test_status = version.test_status
            except:
                test_status = HeuristicTestStatus()
                test_status.heuristic_version = version

            test_status.phase = HeuristicTestStatus.PHASE_STATUS
            test_status.error = False
            test_status.details = ''
            test_status.save()

            # Release the lock
            repo.unlock()

        except:
            repo.unlock()
            raise

        # Tell the experiments scheduler about the new heuristic version
        scheduler = acquireExperimentsScheduler()
        if scheduler is not None:
            scheduler.sendCommand(Message('CHECK_HEURISTIC', [version.id]))
            scheduler.waitResponse()
            releaseExperimentsScheduler(scheduler)

        return HttpResponseRedirect('/heuristics/v%d/' % version.id)


#---------------------------------------------------------------------------------------------------
# Used to change the details of a heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def edit(request, heuristic_id):

    # Retrieve the heuristic
    heuristic_id = int(heuristic_id)
    heuristic = get_object_or_404(Heuristic, pk=heuristic_id)

    # Check that the user has the right to modify it
    if (heuristic.author != request.user) and not(request.user.is_superuser):
        raise Http404

    # Process the form
    form = None
    if (request.method == 'POST') and request.POST.has_key('submit'):

        if request.POST['submit'] == 'Cancel':
            return HttpResponseRedirect('/heuristics/%d/' % heuristic_id)

        form = HeuristicDetailsForm(request.POST, request.user)

        if form.is_valid() and (request.POST['submit'] == 'Save'):

            # The name can only be changed when the heuristic is private
            if (heuristic.latest_public_version is None) and (heuristic.name != form.cleaned_data['name']):
                heuristic.name = form.cleaned_data['name']

                # We must rename all the C++ files accordingly...
                if heuristic.versions_count() > 0:
                    new_filename    = defaultfilters.slugify(heuristic.name.replace(' ', '').replace('-', '_'))
                    files           = []

                    # Retrieve the heuristics repository and lock it
                    heuristicsRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                    heuristicsRepo.lock()

                    try:
                        # Iterate through all the private versions to create the list of filenames to change
                        for version in heuristic.versions.iterator():
                            if not(version.checked):
                                continue

                            if version.version > 1:
                                version_filename = '%s_v%d.cpp' % (new_filename, version.version)
                            else:
                                version_filename = '%s.cpp' % new_filename

                            files.append(('%s/%s' % (heuristic.author.username.lower(), version.filename),
                                          '%s/%s' % (heuristic.author.username.lower(), version_filename)))

                            # Save the new filename in the database
                            version.filename = version_filename
                            version.save()

                        # Rename the files
                        heuristicsRepo.moveFiles(files, "Rename heuristic '%s' to '%s/%s'" % (heuristic.fullname(), heuristic.author.username.lower(),
                                                 new_filename), settings.COMMIT_AUTHOR)

                        # Release the locks
                        heuristicsRepo.unlock()
                    except:
                        heuristicsRepo.unlock()
                        raise

            # Change the other details
            heuristic.short_description = form.cleaned_data['summary']
            heuristic.description = form.cleaned_data['description']

            # Change the inspirations list
            heuristic.inspired_by.clear()
            ids = form.cleaned_data['inspirations_list'].split(';')
            for id in ids:
                if len(id) == 0:
                    continue

                try:
                    inspiration = Heuristic.objects.get(pk=int(id))
                    heuristic.inspired_by.add(inspiration)
                except Heuristic.DoesNotExist:
                    pass

            # Save the heuristic in the database
            heuristic.save()

            # Return to the page of the heuristic
            return HttpResponseRedirect('/heuristics/%d/' % heuristic_id)


    if form is None:
        data = {
            'heuristic_id': heuristic.id,
            'name': heuristic.name,
            'summary': heuristic.short_description,
            'description': heuristic.description,
            'inspirations_list': None,
        }

        inspirations_list = ';'
        for inspiration in heuristic.inspired_by.iterator():
            inspirations_list += '%d;' % inspiration.id
        data['inspirations_list'] = inspirations_list

        form = HeuristicDetailsForm(data, request.user)

    elif hasattr(form, 'cleaned_data'):
        data = form.cleaned_data
    else:
        data = form.data


    return render_to_response('heuristics/edit.html',
                              {'heuristic': heuristic,
                               'form': form,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Delete a specific private version of a heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def delete(request, version_id):

    # Retrieve the version
    version = get_object_or_404(HeuristicVersion, pk=version_id)

    # Check that the user has the right to delete the version
    if ((request.user != version.heuristic.author) and not(request.user.is_superuser)) or version.public:
        raise Http404

    # Retrieve the repository containing the source file and lock it
    if version.checked:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
    else:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
    repo.lock()

    try:
        # Remove the file from the repository
        repo.removeFile('%s/%s' % (request.user.username.lower(), version.filename),
                        "Heuristic '%s' deleted (by %s)" % (version.fullname(), request.user.username),
                        settings.COMMIT_AUTHOR)
    except:
        pass

    # Release the lock
    repo.unlock()

    # Cancel the evaluation experiments still running
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        for evaluation_results in version.evaluation_results.exclude(experiment__status=Experiment.STATUS_DONE):
            scheduler.sendCommand(Message('CANCEL_EXPERIMENT', [evaluation_results.experiment.id]))
            scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)

    # Delete the relevant entries from the database
    try:
        HeuristicTestStatus.objects.filter(heuristic_version__exact=version).delete()
    except:
        pass

    try:
        evaluation_results_list = HeuristicEvaluationResults.objects.filter(heuristic_version__exact=version)

        configurations_to_delete = []
        for evaluation_results in evaluation_results_list:
            configurations_to_delete.append(evaluation_results.experiment.configuration)

        evaluation_results_list.delete()

        for configuration_to_delete in configurations_to_delete:
            configuration_to_delete.delete()
    except:
        pass

    heuristic = version.heuristic
    author = heuristic.author

    version.status = HeuristicVersion.STATUS_DELETED
    version.status_date = datetime.now()
    version.save()

    if heuristic.private_versions_count() > 0:
        heuristic.latest_private_version = heuristic.versions.filter(public=False).exclude(status=HeuristicVersion.STATUS_DELETED).order_by('-version')[0]
    else:
        heuristic.latest_private_version = None

    heuristic.save()

    # Determine if the heuristic isn't referenced by anything anymore, in which case we delete it totally
    if heuristic.was_deleted():
        cannot_delete = (heuristic.derived_heuristics_count() > 0)

        if not(cannot_delete):
            for v in heuristic.versions.iterator():
                if v.configuration_set.count() > 0:
                    cannot_delete = True
                    break

        if not(cannot_delete):
            heuristic.delete()
            heuristic = None

    # Return to the heuristic page
    if (heuristic is not None) and not(heuristic.was_deleted()):
        return HttpResponseRedirect('/heuristics/%d/' % heuristic.id)

    # Return to the list of private heuristics
    return HttpResponseRedirect('/heuristics/private/%d/' % author.id)


#---------------------------------------------------------------------------------------------------
# Handle the publication of a version of a heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def publish(request, version_id):

    # Retrieve the version
    version_id = int(version_id)
    version = get_object_or_404(HeuristicVersion, pk=version_id)

    # Check that the user has the right to modify it
    if ((version.heuristic.author != request.user) and not(request.user.is_superuser)) or \
       version.public or not(version.checked):
        raise Http404

    # Retrieve and validate the arguments
    nb_weeks = 0
    if request.GET.has_key('nb_weeks'):
        try:
            nb_weeks = int(request.GET['nb_weeks'])
            if nb_weeks > 4:
                nb_weeks = 4
            elif nb_weeks < 0:
                nb_weeks = 1
        except:
            pass

    # Determine the new latest private version of the heuristic
    if version.heuristic.latest_private_version == version:
        if version.heuristic.private_versions_count() > 1:
            version.heuristic.latest_private_version = version.heuristic.versions.filter(public=False).exclude(status=HeuristicVersion.STATUS_DELETED).order_by('-version')[1]
        else:
            version.heuristic.latest_private_version = None

    version.public = True
    version.publication_date = datetime.now()
    version.opensource_date = date.today() + timedelta(7 * nb_weeks)
    version.save()

    # Tell the experiments scheduler about the new heuristic
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand('RANK_EVALUATED_HEURISTICS')
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)

        scheduler = acquireExperimentsScheduler()
        if scheduler is not None:
            scheduler.sendCommand('SCHEDULE_PUBLIC_EXPERIMENTS')
            scheduler.waitResponse()
            releaseExperimentsScheduler(scheduler)

    # Enter all the contests we should automatically enter
    all_public_versions = HeuristicVersion.objects.filter(heuristic=version.heuristic, public=True)
    contest_entries = ContestEntry.objects.filter(heuristic_version__in=all_public_versions).filter(
                                                  Q(contest__end__isnull=True) | Q(contest__end__gt=version.publication_date))
    contests = list(set(map(lambda x: x.contest, contest_entries)))

    for contest in contests:
        enter_contest(contest, version)

    return HttpResponseRedirect('/heuristics/v%d/' % version_id)


#---------------------------------------------------------------------------------------------------
# Called to obtain the test status of an heuristic
#---------------------------------------------------------------------------------------------------
def status(request, version_id):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    # Retrieve the heuristic version
    version = get_object_or_404(HeuristicVersion, pk=version_id)

    # Check that the request is legitimate
    if (version.heuristic.author != user) and not(user.is_superuser):
        raise Http404

    # Create the XML result
    result = '<?xml version="1.0" encoding="utf-8"?>'
    result += '<status>'

    # Test if the heuristic was successfully checked
    # No more status info, checking is done

    if version.checked and version.heuristic.simple:
        for phase in HeuristicTestStatus.PHASES:
            result += '<phase>'
            result += '  <name>' + phase[1].lower() + '</name>'
            result += '  <status>done</status>'
            result += '  <statustext>' + HeuristicTestStatus.PHASES_TEXTS[phase[0]][0] + '</statustext>'
            result += '  <details></details>'
            result += '</phase>'

    elif version.checked:
        for phase in HeuristicTestStatus.PHASES:
            result += '<phase>'
            result += '  <name>' + phase[1].lower() + '</name>'
            result += '  <status>done</status>'
            result += '  <statustext>' + HeuristicTestStatus.PHASES_TEXTS[phase[0]][0] + '</statustext>'
            result += '  <details></details>'
            result += '</phase>'

        result += '<phase>'
        result += '  <name>evaluation</name>'

        error = False

        result_configs = ''
        for evaluation_results in version.sortedEvaluationResults():
            result_configs += '  <configuration>'
            result_configs += '    <id>' + str(evaluation_results.evaluation_config.id) + '</id>'
            result_configs += '    <name>' + evaluation_results.evaluation_config.name.replace('template/', '') + '</name>'

            if evaluation_results.experiment.isFailed():
                result_configs += '    <status>error</status>'
                result_configs += '    <statustext>FAILED</statustext>'
                error = True
            elif evaluation_results.experiment.isDone():
                result_configs += '    <status>done</status>'
                result_configs += '    <statustext>OK</statustext>'
            else:
                result_configs += '    <status>inprogress</status>'
                result_configs += '    <statustext>In progress...</statustext>'

            if evaluation_results.experiment.isDone():
                result_configs += '    <meantrainerror>%.2f</meantrainerror>' % (evaluation_results.mean_train_error() * 100)
                result_configs += '    <meantesterror>%.2f</meantesterror>' % (evaluation_results.mean_test_error() * 100)
                result_configs += '    <trainerrorvariance>%.3f</trainerrorvariance>' % (evaluation_results.train_error_standard_deviation() * 100)
                result_configs += '    <testerrorvariance>%.3f</testerrorvariance>' % (evaluation_results.test_error_standard_deviation() * 100)

            if evaluation_results.rank is not None:
                result_configs += '    <rank>' + str(evaluation_results.rank) + '</rank>'

            result_configs += '  </configuration>'

        if error:
            result += '  <status>error</status>'
            result += '  <statustext>FAILED</statustext>'
        elif not(version.evaluated):
            if version.status != HeuristicVersion.STATUS_OK:
                result += '  <status>error</status>'
                result += '  <statustext>FAILED</statustext>'
            else:
                result += '  <status>inprogress</status>'
                result += '  <statustext>In progress...</statustext>'
        else:
            result += '  <status>done</status>'
            result += '  <statustext>OK</statustext>'

        if version.rank is not None:
            result += '  <rank>' + str(version.rank) + '</rank>'

        result += result_configs

        result += '</phase>'

    else:
        # Retrieve the test status
        try:
            test_status = version.test_status
        except:
            test_status                     = HeuristicTestStatus()
            test_status.heuristic_version   = version
            test_status.phase               = HeuristicTestStatus.PHASE_STATUS
            test_status.save()

        for phase in HeuristicTestStatus.PHASES:
            result += '<phase>'
            result +=   '<name>' + phase[1].lower() + '</name>'

            if phase[0] == test_status.phase:
                if test_status.error:
                    result += '<status>error</status>'
                    result += '<statustext>' + HeuristicTestStatus.PHASES_TEXTS[phase[0]][1] + '</statustext>'

                    # Search if some error reports exists
                    try:
                        for report in version.error_reports.all():
                            content = get_error_report_as_html(report, request.user)
                            result += '<errorreport><![CDATA[' + content + ']]></errorreport>'
                    except:
                        pass

                else:
                    result += '<status>inprogress</status>'
                    result += '<statustext>' + HeuristicTestStatus.PHASES_TEXTS[phase[0]][2] + '</statustext>'

                #filtering compilation errors
                if phase[0] == HeuristicTestStatus.PHASE_COMPILATION:
                    filteringInfo = ("%s/%s" % (user,version.filename)).lower()
                    filteredInfo = ''

                    lines = test_status.details.split("\n")
                    for line in lines:
                        if line.lower().startswith(filteringInfo):
                            filteredInfo += line
                            filteredInfo += "\n"

                    resultOutput = ''
                    if len(filteredInfo) != 0:
                        resultOutput = test_status.details.split("\n")[0]+"\n\n"+filteredInfo
                    else :
                        resultOutput = test_status.details

                    result += '<details>' + resultOutput.replace('&', '&amp;').replace('<', '&lt;').replace('<', '&gt;') + '</details>'
                else:
                    result += '<details>' + test_status.details.replace('&', '&amp;').replace('<', '&lt;').replace('<', '&gt;') + '</details>'

            else:
                result += '<status>done</status>'
                result += '<statustext>' + HeuristicTestStatus.PHASES_TEXTS[phase[0]][0] + '</statustext>'
                result += '<details></details>'

            result += '</phase>'

            # This is the current phase, exit the loop
            if phase[0] == test_status.phase:
                break

    result += '</status>'

    #print result

    return getHttpResponse(result)


def getHttpResponse(result):
    """Build an http response that prevent ajax cache in IE8"""

    response = HttpResponse(mimetype="text/xml")
    response["Cache-Control"] = "max-age=0,no-cache,no-store"
    response.write(result)

    return response


#---------------------------------------------------------------------------------------------------
# Called to test if a heuristic name isn't already used
#---------------------------------------------------------------------------------------------------
def test_heuristic_name(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    user = process_cookie(request)

    if request.GET.has_key('filename'):
        filename = request.GET['filename']
    else:
        raise Http404

    # Remove the file extension
    (heuristic_name, extensions) = os.path.splitext(filename)
    heuristic_name = defaultfilters.slugify(heuristic_name.strip().replace(' ', '').replace('-', '_'))

    # Retrieve the heuristic version
    response = HttpResponse(mimetype="text/plain")

    try:
        heuristic = Heuristic.objects.filter(name=heuristic_name).filter(author__id=user.id)[0]
        response.write('%d' % heuristic.id)
    except:
        response.write('OK')

    return response


#---------------------------------------------------------------------------------------------------
# Displayed when the user ask to cancel the upload of a heuristic
#---------------------------------------------------------------------------------------------------
@login_required
def cancel_upload(request):

    # Retrieve the heuristic currently tested for the current user
    heuristic = get_object_or_404(Heuristic, author__exact=request.user, checked__exact=False)


    # Process the form
    if (request.method == 'POST') and (request.POST.has_key('submit') or request.POST.has_key('cancel')):

        if request.POST.has_key('cancel'):
            return HttpResponseRedirect('/heuristics/test/')

        # Retrieve the upload repository and lock it
        uploadRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        uploadRepo.lock()

        try:
            # Remove the file from the upload repository
            uploadRepo.removeFile('%s/%s' % (request.user.username.lower(), heuristic.filename),
                                  "File '%s' of user '%s' cancelled" %
                                  (heuristic.filename, request.user.username),
                                  settings.COMMIT_AUTHOR)

            # If the upload repository is empty, destroy it (no need to keep an history of the uploaded files)
            if not(uploadRepo.repository().tree().values()):
                uploadRepo.delete()

            # Release the locks
            uploadRepo.unlock()

            heuristic.delete()

            return HttpResponseRedirect('/accounts/profile/?p=h')

        except:
            uploadRepo.unlock()
            raise

    return render_to_response('heuristics/cancel_upload.html',
                              {},
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display the difference between the source code of two heuristics
#---------------------------------------------------------------------------------------------------
def diff(request):

    def _getArgumentValue(argument):
        try:
            return int(request.GET[argument])
        except:
            return None

    def _getHeuristic(heuristic_id, version_id):
        if version_id is not None:
            version = get_object_or_404(HeuristicVersion, pk=version_id)
            if version.public or (version.heuristic.author == request.user) or (request.user.is_superuser):
                return version
        elif heuristic_id is not None:
            heuristic = get_object_or_404(Heuristic, pk=heuristic_id)
            if (heuristic.author == request.user) or (request.user.is_superuser and not heuristic.latest_public_version):
                return heuristic.latest_version()
            else:
                return heuristic.latest_public_version
        return None

    def _getSourceCode(version):
        # Retrieve the repository and lock it
        if version.checked:
            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
        else:
            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        repo.lock()

        try:
            # Retrieve the source code file from the repository
            blob = repo.repository().tree()[version.heuristic.author.username.lower()][version.filename]

            # Release the lock
            repo.unlock()

        except:
            repo.unlock()
            # Not checked, can be in heuristics directory too (during evaluation)
            try:
                repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                repo.lock()

                blob = repo.repository().tree()[version.heuristic.author.username.lower()][version.filename]

                repo.unlock()
            except:
                repo.unlock()
                raise

        return blob


    # Declarations
    new = None
    old = None
    new_version = None
    old_version = None

    # Retrieve and validate the arguments
    new = _getArgumentValue('n')
    old = _getArgumentValue('o')
    new_version = _getArgumentValue('vn')
    old_version = _getArgumentValue('vo')

    # Retrieve the versions of the heuristics to compare
    new_heuristic_version = _getHeuristic(new, new_version)
    old_heuristic_version = _getHeuristic(old, old_version)

    # Check that the heuristics are valid
    if (new_heuristic_version is None) or (old_heuristic_version is None) or \
       (new_heuristic_version == old_heuristic_version):
        raise Http404

    # Retrieve the source codes
    new_blob = _getSourceCode(new_heuristic_version)
    old_blob = _getSourceCode(old_heuristic_version)

    # Perform the diff
    differ = difflib.Differ()
    diff = differ.compare(old_blob.data.splitlines(), new_blob.data.splitlines())

    diff_table = '<table><tbody>'

    old_counter = 1
    new_counter = 1
    for line in diff:
        lineclass = ''
        oldline = None
        newline = None

        if line.startswith('+'):
            lineclass = 'add'
            newline = new_counter
            new_counter += 1
        elif line.startswith('-'):
            lineclass = 'del'
            oldline = old_counter
            old_counter += 1
        elif line.startswith('?'):
            continue
        else:
            lineclass = 'unmod'
            oldline = old_counter
            newline = new_counter
            old_counter += 1
            new_counter += 1

        diff_table += '<tr class="%s">' % lineclass

        if oldline is not None:
            diff_table += '<td id="old-line-%d" class="lineno"><pre><a href="#old-line-%d">%d</a></pre></td>' % (oldline, oldline, oldline)
        else:
            diff_table += '<td class="lineno"><pre>&nbsp;</pre></td>'

        if newline is not None:
            diff_table += '<td id="new-line-%d" class="lineno new"><pre><a href="#new-line-%d">%d</a></pre></td>' % (newline, newline, newline)
        else:
            diff_table += '<td class="lineno"><pre>&nbsp;</pre></td>'

        text = line[2:].replace('<', '&lt;').replace('>', '&gt;').expandtabs(4)

        diff_table += '<td class="code"><pre>%s</pre></td>' % text

        diff_table += '</tr>'

    diff_table += '</tbody></table>'

    # Rendering
    return render_to_response('heuristics/diff.html',
                              {'new_heuristic_version': new_heuristic_version,
                               'old_heuristic_version': old_heuristic_version,
                               'diff_table': diff_table, },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Handle the creation of/redirection to the official forum topic of a heuristic
#---------------------------------------------------------------------------------------------------
def topic(request, heuristic_id):

    # Retrieve the heuristic
    heuristic = get_object_or_404(Heuristic, pk=heuristic_id)

    # Create the heuristic topic if it don't already exists
    if heuristic.post is None:
        createTopic(heuristic, 'Heuristics', heuristic.fullname(),
                    'heuristics/%d/' % heuristic.id, 'heuristic')

    # Go to the topic
    return HttpResponseRedirect('/forum/viewtopic.php?t=%d' % heuristic.post.topic.topic_id)

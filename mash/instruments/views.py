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


from mash.instruments.models import DataReport, View, ViewFile, Snippet
from mash.experiments.models import Configuration
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.http import HttpResponse, Http404
from django.core.files import locks
import datetime
import os
import subprocess
import tarfile
import shutil


#---------------------------------------------------------------------------------------------------
# Display a data report
#---------------------------------------------------------------------------------------------------
def report(request, report_id):

    # Retrieve the report
    report = get_object_or_404(DataReport, pk=report_id)

    # Check that the user has the right to see the report
    if report.experiment is not None:
        if (report.experiment.configuration.experiment_type == Configuration.PRIVATE) and \
           (request.user != report.experiment.user) and not(request.user.is_superuser):
           raise Http404

        elif (report.experiment.configuration.experiment_type == Configuration.CONSORTIUM) and \
             (request.user.is_anonymous() or not(request.user.get_profile().project_member)):
            raise Http404

        elif (report.experiment.configuration.experiment_type == Configuration.EVALUATION) and \
            not(request.user.is_superuser):
            raise Http404


    snippets = []
    snippets_css_files = []
    snippets_js_files = []
    try:
        for instrument in report.instruments_set.iterator():
            (report_snippets, report_snippets_css_files, report_snippets_js_files) = get_snippets(report, instrument)
            if report_snippets is None:
                continue

            snippets.extend(report_snippets)
            snippets_css_files.extend(filter(lambda x: x not in snippets_css_files, report_snippets_css_files))
            snippets_js_files.extend(filter(lambda x: x not in snippets_css_files, report_snippets_js_files))
    except:
        pass


    if snippets is None:
        return render_to_response('instruments/no_view.html',
                                  {'report': report,
                                  },
                                  context_instance=RequestContext(request))

    # Rendering
    return render_to_response('instruments/report.html',
                              {'report': report,
                               'css_files': snippets_css_files,
                               'js_files': snippets_js_files,
                               'snippets': snippets,
                              },
                              context_instance=RequestContext(request))


def snippet(request, snippet_id):

    def _deleteUncompressedReport(report):
        sibling_snippets = Snippet.objects.filter(report=report, status=Snippet.GENERATING)
        if sibling_snippets.count() == 0:
            current_dir = os.getcwd()
            os.chdir(os.path.join(settings.DATA_REPORTS_ROOT, snippet.report.parentfolder()))

            decompressedfolder = snippet.report.decompressedfolder()
            if os.path.exists(decompressedfolder):
                shutil.rmtree(decompressedfolder)

            os.chdir(current_dir)

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    # Setup the locking mechanism
    filename = os.path.join(settings.SNIPPETS_ROOT, 'snippets.lock')
    lock_file = open(filename, 'wb')
    try:
        os.chmod(filename, 0766)
    except:
        pass
    locks.lock(lock_file, locks.LOCK_EX)

    # Retrieve the snippet
    snippet = get_object_or_404(Snippet, pk=snippet_id)

    # Ensure that it wasn't already generated
    if snippet.status == Snippet.AVAILABLE:
        locks.unlock(lock_file)
        lock_file.close()
        response = HttpResponse(mimetype="text/xml")
        response["Cache-Control"] = "max-age=0,no-cache,no-store"
        response.write(snippet.content())
        return response

    # Ensure that the generation didn't failed
    if snippet.status == Snippet.ERROR:
        locks.unlock(lock_file)
        lock_file.close()
        response = HttpResponse(mimetype="text/xml")
        response["Cache-Control"] = "max-age=0,no-cache,no-store"
        response.write('ERROR')
        return response

    # Ensure that the generation isn't in progress
    if snippet.status == Snippet.GENERATING:
        locks.unlock(lock_file)
        lock_file.close()
        response = HttpResponse(mimetype="text/xml")
        response["Cache-Control"] = "max-age=0,no-cache,no-store"
        response.write('UNAVAILABLE')
        return response

    # Uncompress the report files if necessary
    sibling_snippets = Snippet.objects.filter(report=snippet.report, status=Snippet.GENERATING)
    if sibling_snippets.count() == 0:
        current_dir = os.getcwd()
        os.chdir(os.path.join(settings.DATA_REPORTS_ROOT, snippet.report.parentfolder()))

        decompressedfolder = snippet.report.decompressedfolder()
        if not(os.path.exists(decompressedfolder)):
            os.makedirs(decompressedfolder)
            tar = tarfile.open(snippet.report.archivename(), 'r:gz')
            tar.extractall(path=decompressedfolder)
            tar.close()

        os.chdir(current_dir)

    # Update the status
    snippet.status = Snippet.GENERATING
    snippet.save()

    locks.unlock(lock_file)

    try:
        # Execute the script of the view
        if not(os.path.exists(os.path.join(settings.SNIPPETS_ROOT, snippet.folder))):
            os.makedirs(os.path.join(settings.SNIPPETS_ROOT, snippet.folder))
        current_dir = os.getcwd()
        os.chdir(os.path.join(settings.INSTRUMENTS_ROOT, snippet.view.instrument.fullname()))

        p = subprocess.Popen('./%s %s %s /snippets/%s' % (snippet.view.script, os.path.join(settings.DATA_REPORTS_ROOT, snippet.report.parentfolder(), snippet.report.decompressedfolder()),
                                                          os.path.join(settings.SNIPPETS_ROOT, snippet.folder), snippet.folder),
                             shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if p.wait() == 0:
            locks.lock(lock_file, locks.LOCK_EX)
            snippet.status = Snippet.AVAILABLE
            snippet.save()
            _deleteUncompressedReport(snippet.report)
            locks.unlock(lock_file)
        else:
            print p.stdout.read()
            raise IOError

        os.chdir(current_dir)
    except:
        locks.lock(lock_file, locks.LOCK_EX)
        snippet.status = Snippet.ERROR
        snippet.save()
        _deleteUncompressedReport(snippet.report)
        locks.unlock(lock_file)
        lock_file.close()
        response = HttpResponse(mimetype="text/xml")
        response["Cache-Control"] = "max-age=0,no-cache,no-store"
        response.write('ERROR')
        return response

    lock_file.close()

    # Return the content of the snippet
    response = HttpResponse(mimetype="text/xml")
    response["Cache-Control"] = "max-age=0,no-cache,no-store"
    response.write(snippet.content())
    return response


def get_snippets_static_files(instrument):

    # Retrieve the list of static CSS and Javascript files needed by the views of the instrument
    css_files = []
    js_files = []

    instrument_css_files = ViewFile.objects.filter(view__instrument=instrument, static=True, type=ViewFile.CSS)
    for css_file in instrument_css_files:
        if css_file.shared:
            path = '/instruments/static/%s' % css_file.filename
        else:
            path = '/instruments/%s/%s' % (css_file.view.instrument.fullname(), css_file.filename)

        if path not in css_files:
            css_files.append(path)

    instrument_js_files = ViewFile.objects.filter(view__instrument=instrument, static=True, type=ViewFile.JAVASCRIPT)
    for js_file in instrument_js_files:
        if js_file.require is not None:
            if js_file.require.shared:
                path = '/js/%s' % js_file.require.filename
            else:
                path = '/instruments/%s/%s' % (js_file.require.view.instrument.fullname(), js_file.require.filename)

            if path not in js_files:
                js_files.append(path)

        if js_file.shared:
            path = '/js/%s' % js_file.filename
        else:
            path = '/instruments/%s/%s' % (js_file.view.instrument.fullname(), js_file.filename)

        if path not in js_files:
            js_files.append(path)

    return (css_files, js_files)


def get_or_create_snippet(report, view):
    try:
        snippet = Snippet.objects.get(report=report, view=view)
    except:
        now = datetime.datetime.now()
        snippets_folder = os.path.join(str(now.year), str(now.month), str(now.day),
                                       str(now.hour), str(now.minute), str(now.second))

        snippet         = Snippet()
        snippet.report  = report
        snippet.view    = view
        snippet.folder  = os.path.join(snippets_folder, str(report.id), view.fullname())
        snippet.status  = Snippet.UNAVAILABLE
        snippet.save()

    return snippet


def get_snippets(report, instrument, used_in_experiment_results=None, used_in_factory_results=None):

    # Retrieve all the views linked to the instrument
    views = View.objects.filter(instrument=instrument)
    if views.count() == 0:
        return (None, None, None)

    # Create the missing snippet database entries
    now = datetime.datetime.now()
    snippets_folder = os.path.join(str(now.year), str(now.month), str(now.day),
                                   str(now.hour), str(now.minute), str(now.second))

    for view in views.iterator():
        snippets = Snippet.objects.filter(report=report, view=view)
        if snippets.count() == 0:
            snippet         = Snippet()
            snippet.report  = report
            snippet.view    = view
            snippet.folder  = os.path.join(snippets_folder, str(report.id), view.fullname())
            snippet.status  = Snippet.UNAVAILABLE
            snippet.save()

    # Retrieve all the snippets
    snippets = Snippet.objects.filter(report=report, view__instrument=instrument).exclude(status=Snippet.ERROR)

    if used_in_experiment_results is not None:
        snippets = snippets.filter(view__used_in_experiment_results=used_in_experiment_results)

    if used_in_factory_results is not None:
        snippets = snippets.filter(view__used_in_factory_results=used_in_factory_results)

    # Retrieve the list of static CSS and Javascript files needed by the snippets
    css_files = []
    js_files = []
    for snippet in snippets:
        snippet_css_files = ViewFile.objects.filter(view=snippet.view, static=True, type=ViewFile.CSS)
        for css_file in snippet_css_files:
            if css_file.shared:
                path = '/instruments/static/%s' % css_file.filename
            else:
                path = '/instruments/%s/%s' % (css_file.view.instrument.fullname(), css_file.filename)

            if path not in css_files:
                css_files.append(path)

        snippet_js_files = ViewFile.objects.filter(view=snippet.view, static=True, type=ViewFile.JAVASCRIPT)
        for js_file in snippet_js_files:
            if js_file.require is not None:
                if js_file.require.shared:
                    path = '/js/%s' % js_file.require.filename
                else:
                    path = '/instruments/%s/%s' % (js_file.require.view.instrument.fullname(), js_file.require.filename)

                if path not in js_files:
                    js_files.append(path)

            if js_file.shared:
                path = '/js/%s' % js_file.filename
            else:
                path = '/instruments/%s/%s' % (js_file.view.instrument.fullname(), js_file.filename)

            if path not in js_files:
                js_files.append(path)

    return (snippets, css_files, js_files)

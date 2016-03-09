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


from django.shortcuts import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from mash.servers.models import Server
from mash.servers.forms import NewServerForm
from pymash.messages import Message
from servers import acquireExperimentsScheduler, releaseExperimentsScheduler



####################################################################################################
#
# VIEWS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Display the list of servers
#---------------------------------------------------------------------------------------------------
@login_required
def servers_list(request):

    # Check that the user has the right to see that
    if not(request.user.is_superuser):
        raise Http404           
        
    # Retrieve the servers
    compilation_servers  = Server.objects.filter(server_type=Server.COMPILATION_SERVER).order_by('name')
    debugging_servers    = Server.objects.filter(server_type=Server.DEBUGGING_SERVER).order_by('name')
    experiments_servers  = Server.objects.filter(server_type=Server.EXPERIMENTS_SERVER).order_by('name')
    application_servers  = Server.objects.filter(server_type=Server.APPLICATION_SERVER).order_by('name')
    clustering_servers   = Server.objects.filter(server_type=Server.CLUSTERING_SERVER).order_by('name')
    unknown_servers      = Server.objects.filter(server_type=Server.UNKNOWN_SERVER).order_by('name')
    unidentified_servers = Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).order_by('name')
    
    # Start the check of the status of the servers
    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand('CHECK_SERVERS_STATUS')
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)
    
    # Rendering
    return render_to_response('servers/status.html',
                              {'nb_servers': compilation_servers.count() + experiments_servers.count() +
                                             application_servers.count() + unknown_servers.count(),
                               'compilation_servers': compilation_servers,
                               'debugging_servers': debugging_servers,
                               'experiments_servers': experiments_servers,
                               'application_servers': application_servers,
                               'clustering_servers': clustering_servers,
                               'unknown_servers': unknown_servers,
                               'unidentified_servers': unidentified_servers,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Used to add a new server
#---------------------------------------------------------------------------------------------------
@login_required
def server_add(request):

    # Check that the user has the right to do that
    if not(request.user.is_superuser):
      raise Http404           

    # Process the form
    form = None
    if (request.method == 'POST') and request.POST.has_key('submit'):

        if request.POST['submit'] == 'Cancel':
            return HttpResponseRedirect('/servers/')

        form = NewServerForm(request.POST)

        if form.is_valid() and (request.POST['submit'] == 'Add'):

            # Save the server in the database
            server                      = Server()
            server.name                 = form.cleaned_data['name']
            server.address              = form.cleaned_data['address']
            server.port                 = form.cleaned_data['port']
            server.server_type          = Server.UNKNOWN_SERVER
            server.subtype              = Server.SUBTYPE_NONE
            server.heuristic_version    = None
            server.experiment           = None
            server.save()

            # Return to the list of servers
            return HttpResponseRedirect('/servers/')

    if form is None:
        form = NewServerForm()

    # Rendering
    return render_to_response('servers/add.html',
                              { 'form': form },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Called to obtain the status of the servers
#---------------------------------------------------------------------------------------------------
@login_required
def servers_status(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    # Check that the user has the right to do that
    if not(request.user.is_superuser):
        raise Http404           

    # Retrieve a list of the servers for which the status is known
    servers = Server.objects.exclude(status=Server.SERVER_STATUS_UNKNOWN)
    
    # Create the XML result
    result = '<?xml version="1.0" encoding="utf-8"?>'
    result += '<status>'

    for server in servers:
        result += '<server>'
        result +=   '<id>' + str(server.id) + '</id>'

        if server.status == Server.SERVER_STATUS_ONLINE:
            result += '<status>online</status>'
        else:
            result += '<status>offline</status>'

        result += '</server>'
    
    result += '</status>'
        
    return HttpResponse(result, mimetype="text/xml")


#---------------------------------------------------------------------------------------------------
# Called to identify a particular server
#---------------------------------------------------------------------------------------------------
@login_required
def server_identify(request, server_id):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404
    
    # Check that the user has the right to do that
    if not(request.user.is_superuser):
        raise Http404           

    # Retrieve the server
    server = Server.objects.get(id=server_id)

    # If the server is unknown, ask the Scheduler to identify it
    if server.server_type == Server.UNKNOWN_SERVER:
        scheduler = acquireExperimentsScheduler()
        if scheduler is not None:
            server.server_type = Server.UNIDENTIFIED_SERVER
            server.save()

            scheduler.sendCommand(Message('IDENTIFY_SERVER', [server_id]))
            scheduler.waitResponse()
            releaseExperimentsScheduler(scheduler)
        else:
            return HttpResponse("%s FAILED" % server_id, mimetype="text/plain")

    return HttpResponse("%s %s" % (server_id, filter(lambda x: x[0] == server.server_type, Server.SERVER_TYPES)[0][1]), mimetype="text/plain")


#---------------------------------------------------------------------------------------------------
# Ask the Scheduler to execute a particular command
#---------------------------------------------------------------------------------------------------
@login_required
def execute(request, command):

    # Check that the user has the right to do that
    if not(request.user.is_superuser):
        raise Http404           

    scheduler = acquireExperimentsScheduler()
    if scheduler is not None:
        scheduler.sendCommand(command)
        scheduler.waitResponse()
        releaseExperimentsScheduler(scheduler)

    return HttpResponseRedirect('/servers/')

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


from tasks.task import Task
from tasks.jobs import Job
from utilities.logs import getServerLogs
from pymash import Client
from pymash import Message
from pymash.gitrepository import GitRepository
from django.conf import settings
from django.template import defaultfilters
from servers.models import Server
from servers.models import Alert
from heuristics.models import HeuristicVersion
from heuristics.models import HeuristicTestStatus
from factory.models import FactoryTask
from factory.models import DebuggingEntry
from tools.models import PluginErrorReport
import os
import traceback
from datetime import datetime


#-------------------------------------------------------------------------------
# This task record debugging informations for a heuristic
#-------------------------------------------------------------------------------
class HeuristicDebugger(Task):

    SUPPORTED_COMMANDS = { 'DEBUG_HEURISTIC': [int] }   # <debugging_entry_id> 
    SUPPORTED_EVENTS   = {}


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        for debugging_entry in DebuggingEntry.objects.filter(status=DebuggingEntry.STATUS_RUNNING):
            self.jobs.addJob(command=Message('DEBUG_HEURISTIC', [debugging_entry.id]))

        for debugging_entry in DebuggingEntry.objects.filter(status=DebuggingEntry.STATUS_SCHEDULED):
            self.jobs.addJob(command=Message('DEBUG_HEURISTIC', [debugging_entry.id]))


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        # Retrieve the debugging entry
        try:
            job.debugging_entry = DebuggingEntry.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown debugging entry ID: %d' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Search a free Interactive Application Server suitable for this experiment
        goal_name = job.debugging_entry.task.config.goalName()
        environment_name = job.debugging_entry.task.config.environmentName()

        job.outStream.write("Searching a free Interactive Application Server providing " \
                             "the goal '%s' and the environment '%s'...\n" % (goal_name, environment_name))

        servers = Server.objects.filter(server_type=Server.APPLICATION_SERVER, subtype=Server.SUBTYPE_INTERACTIVE,
                                        provided_goals__name__in=[goal_name],
                                        provided_goals__environments__name__in=[environment_name])

        job.application_server = None
        for server in servers:
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            client = Client()
            if client.connect(server.address, server.port):
                client.sendCommand('STATUS')
                response = client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Interactive Application Server found\n")
                    job.application_server = server

            client.close()
            del client

            if job.application_server is not None:
                break

        if job.application_server is None:
            job.outStream.write("Failed to find a free Interactive Application providing " \
                                 "the goal '%s' and the environment '%s'...\n" % (goal_name, environment_name))
            job.markAsDelayed(60)
            return

        # Search a free Debugging Server
        job.outStream.write("Searching a free debugging server...\n")

        servers = Server.objects.filter(server_type=Server.DEBUGGING_SERVER)
        for server in filter(lambda x: x.current_job() is None, servers):
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            job.client = Client(outStream = job.outStream)
            if job.client.connect(server.address, server.port):
                job.client.sendCommand('STATUS')
                response = job.client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Debugging Server found\n")
                    job.markAsRunning(server=server, heuristic_version=job.debugging_entry.heuristic_version)
                    break

            job.client.close()
            del job.client
            job.client = None

        if job.client is None:
            job.outStream.write("Failed to find a free debugging server\n")
            job.markAsDelayed(60)
            return

        # Indicates that the debugging entry is being processed
        job.debugging_entry.status = DebuggingEntry.STATUS_RUNNING
        job.debugging_entry.save()

        # Tell the Debugging Server about the Application Server to use
        if not(job.client.sendCommand(Message('USE_APPLICATION_SERVER', [job.application_server.address, job.application_server.port]))):
            self.processError(job, 'Failed to select the Application Server')
            return

        job.operation = HeuristicDebugger.selectTask


    #---------------------------------------------------------------------------
    # Process the response to the 'USE_APPLICATION_SERVER' command and select
    # the task
    #---------------------------------------------------------------------------
    def selectTask(self, job):

        response = job.client.waitResponse()
        if (response is None) or (response.name != 'OK'):
            alert = Alert()
            alert.message = 'Failed to select the Application Server'

            job.outStream.write("ERROR - %s\n" % alert.message)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s' % alert.message
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        # Select the task
        job.outStream.write("Selecting the task...\n")
        if not(job.client.sendCommand(Message('SELECT_TASK', [job.debugging_entry.task.config.goalName(), job.debugging_entry.task.config.environmentName()]))):
            alert = Alert()
            alert.message = "Failed to tell the server about the task (goal: %s, environment: %s)" % (job.debugging_entry.task.config.goalName(),
                                                                                                      job.debugging_entry.task.config.environmentName())

            job.outStream.write("ERROR - %s\n" % alert.message)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s' % alert.message
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.operation = HeuristicDebugger.sendHeuristicsRepository


    #---------------------------------------------------------------------------
    # Process the response to the 'SELECT_TASK' command and thell the server
    # about the heuristics repository
    #---------------------------------------------------------------------------
    def sendHeuristicsRepository(self, job):

        response = job.client.waitResponse()
        if (response is None) or (response.name != 'OK'):
            alert = Alert()
            alert.message = 'Failed to select the task'
            alert.details = "Goal: %s\nEnvironment: %s" % (job.debugging_entry.task.config.goalName(),
                                                           job.debugging_entry.task.config.environmentName())

            if response is not None:
                alert.details += "\nResponse: %s" % response.toString()

            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s\n%s' % (alert.message, alert.details)
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        # Tell the server about the heuristics repository
        job.outStream.write("Tell the server about the heuristics repository...\n")
        if not(job.client.sendCommand(Message('USE_HEURISTICS_REPOSITORY',
                                              [settings.REPOSITORY_HEURISTICS_URL]))):
            alert = Alert()
            alert.message = 'Failed to tell the server about the heuristics repository'

            job.outStream.write("ERROR - %s\n" % alert.message)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s' % alert.message
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.operation = HeuristicDebugger.startHeuristicDebugging


    #---------------------------------------------------------------------------
    # Process the response to the 'USE_HEURISTICS_REPOSITORY' command and start
    # the debugging of the heuristic
    #---------------------------------------------------------------------------
    def startHeuristicDebugging(self, job):
        
        response = job.client.waitResponse()
        if (response is None) or (response.name != 'OK'):
            alert = Alert()
            alert.message = 'Failed to select the heuristics repository'
            alert.details = "Repository: %s" % settings.REPOSITORY_HEURISTICS_URL

            if response is not None:
                alert.details += "\nResponse: %s" % response.toString()

            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s\n%s' % (alert.message, alert.details)
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        # Debug the heuristic
        job.outStream.write("Debug the heuristic...\n")

        if job.debugging_entry.start_frame < 0:
            args = [job.server_job.heuristic_version.fullname(), job.debugging_entry.sequence]
        elif job.debugging_entry.end_frame < 0:
            args = [job.server_job.heuristic_version.fullname(), job.debugging_entry.sequence, job.debugging_entry.start_frame]
        else:
            args = [job.server_job.heuristic_version.fullname(), job.debugging_entry.sequence, job.debugging_entry.start_frame, job.debugging_entry.end_frame]

        if not(job.client.sendCommand(Message('DEBUG_HEURISTIC', args))):
            alert = Alert()
            alert.message = "Failed to tell the server to debug the heuristic '%s'" % job.server_job.heuristic_version.fullname()

            job.outStream.write("ERROR - %s\n" % alert.message)

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s' % alert.message
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.operation = HeuristicDebugger.processDebuggingResult


    #---------------------------------------------------------------------------
    # Process the result of the debugging of the heuristic
    #---------------------------------------------------------------------------
    def processDebuggingResult(self, job):
        response = job.client.waitResponse()
        if (response is None) or (response.name != 'DATA'):
            alert = Alert()
            alert.message = "Failed to debug the heuristic '%s'" % job.server_job.heuristic_version.fullname()

            if response is not None:
                alert.details = "Response: %s" % response.toString()

            job.outStream.write("ERROR - %s\n%s\n" % (alert.message, alert.details.encode('ascii', 'ignore')))

            job.debugging_entry.status = DebuggingEntry.STATUS_ERROR
            job.debugging_entry.error_details = '%s\n%s' % (alert.message, alert.details)
            job.debugging_entry.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        # Save the data
        size = response.parameters[0]

        data = job.client.waitData(size)

        fullpath = os.path.join(settings.HEURISTICS_DEBUGGING_ROOT, job.debugging_entry.filename())
        if not(os.path.exists(os.path.dirname(fullpath))):
            os.makedirs(os.path.dirname(fullpath))

        outFile = open(fullpath, 'wb')
        outFile.write(data)
        outFile.close()

        # Save the info in the database
        job.debugging_entry.status = DebuggingEntry.STATUS_DONE
        job.debugging_entry.save()

        job.outStream.write("Debugging done\n")

        job.client.sendCommand('DONE')
        job.client.close()
        del job.client
        job.client = None

        # Mark the job as done
        job.markAsDone()



def tasks():
    return [HeuristicDebugger]

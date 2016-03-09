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
from experiments.models import Configuration
from tools.models import PluginErrorReport
import os
import traceback
from datetime import datetime


#-------------------------------------------------------------------------------
# This task tries to compile and test a heuristic
#-------------------------------------------------------------------------------
class HeuristicChecker(Task):

    SUPPORTED_COMMANDS = { 'CHECK_HEURISTIC': [int] }   # <heuristic_version_id>
    SUPPORTED_EVENTS   = {}


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        # Retrieve the heuristic version
        try:
            heuristic_version = HeuristicVersion.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown heuristic version ID: %d' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Search a free Compilation Server
        job.outStream.write("Searching a free compilation server...\n")
        
        servers = Server.objects.filter(server_type=Server.COMPILATION_SERVER)
        for server in filter(lambda x: x.current_job() is None, servers):
            job.outStream.write("    Contacting '%s:%d'...\n" % (server.address, server.port))

            job.client = Client(outStream = job.outStream)
            if job.client.connect(server.address, server.port):
                job.client.sendCommand('STATUS')
                response = job.client.waitResponse()
                if response.name == 'READY':
                    job.outStream.write("    Compilation Server found\n")
                    job.markAsRunning(server=server, heuristic_version=heuristic_version)
                    break
            
            job.client.close()
            del job.client
            job.client = None

        if job.client is None:
            job.outStream.write("Failed to find a free compilation server\n")
            job.markAsDelayed(60)
            return
        
        # Create the test status
        try:
            job.test_status = heuristic_version.test_status
        except:
            job.test_status = HeuristicTestStatus()
        
        job.test_status.heuristic_version = heuristic_version
        job.test_status.phase = HeuristicTestStatus.PHASE_STATUS
        job.test_status.save()
        
        # Tell the server about the heuristics repository
        job.outStream.write("Tell the server about the heuristics repository...\n")
        if not(job.client.sendCommand(Message('USE_HEURISTICS_REPOSITORY',
                                              [settings.REPOSITORY_UPLOAD_URL]))):
            alert = Alert()
            alert.message = 'Failed to tell the server about the heuristics repository'
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            job.test_status.error = True
            job.test_status.details = alert.message
            job.test_status.save()
            return

        job.operation = HeuristicChecker.startHeuristicCheck


    #---------------------------------------------------------------------------
    # Process the response to the 'USE_HEURISTICS_REPOSITORY' command and start
    # the check of the heuristic
    #---------------------------------------------------------------------------
    def startHeuristicCheck(self, job):
        
        response = job.client.waitResponse()
        if response.name != 'OK':
            alert = Alert()
            alert.message = 'Failed to select the heuristics repository'
            alert.details = "Repository: %s\nResponse: %s" % (os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD),
                                                                 response.toString())
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.outStream.write("        %s\n" % alert.details)

            job.test_status.error = True
            job.test_status.details = '%s\n%s' % (alert.message, alert.details)
            job.test_status.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        # Enter the 'Compilation' phase
        job.test_status.phase = HeuristicTestStatus.PHASE_COMPILATION
        job.test_status.save()

        # Check the heuristic
        job.outStream.write("Check the heuristic...\n")
        if not(job.client.sendCommand(Message('CHECK_HEURISTIC', [job.server_job.heuristic_version.fullname()]))):
            alert = Alert()
            alert.message = "Failed to tell the server to check the heuristic '%s'" % job.server_job.heuristic_version.fullname()
            job.outStream.write("ERROR - %s\n" % alert.message)

            job.test_status.error = True
            job.test_status.details = alert.message
            job.test_status.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.operation = HeuristicChecker.processCompilationResult


    #---------------------------------------------------------------------------
    # Process the result of the compilation of the heuristic version
    #---------------------------------------------------------------------------
    def processCompilationResult(self, job):
        response = job.client.waitResponse()
        if response.name != 'COMPILATION_OK':
            alert = Alert()

            if response.name == 'ERROR':
                alert.message = "Failed to check the heuristic '%s'" % job.server_job.heuristic_version.fullname()
                alert.details = "Error during the compilation phase: %s" % response.parameters[0]
            elif response.name == 'COMPILATION_ERROR':
                alert.message = "Failed to compile the heuristic '%s'" % job.server_job.heuristic_version.fullname()
                alert.details = unicode(response.parameters[0], 'utf-8')
            else:
                alert.message = "Failed to check the heuristic '%s'" % job.server_job.heuristic_version.fullname()
                alert.details = "Unknown response from the Compilation Server. Expected: COMPILATION_OK, got: %s" % response.toString()

            job.outStream.write("ERROR - %s\n%s\n" % (alert.message, alert.details.encode('ascii', 'ignore')))

            job.test_status.heuristic_version.status = HeuristicVersion.STATUS_DISABLED
            job.test_status.heuristic_version.status_date = datetime.now()
            job.test_status.heuristic_version.save()

            job.test_status.error = True
            job.test_status.details = '%s\n%s' % (alert.message, alert.details.encode('ascii', 'ignore'))
            job.test_status.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.outStream.write("Compilation OK\n")

        # Enter the 'Analysis' phase
        job.test_status.phase = HeuristicTestStatus.PHASE_ANALYZE
        job.test_status.save()

        job.operation = HeuristicChecker.processAnalysisResult


    #---------------------------------------------------------------------------
    # Process the result of the analysis of the heuristic version
    #---------------------------------------------------------------------------
    def processAnalysisResult(self, job):
        response = job.client.waitResponse()
        if response.name != 'ANALYZE_OK':
            alert = Alert()

            if response.name == 'ANALYZE_ERROR':
                alert.message = "Failed to analyze the heuristic '%s'" % job.server_job.heuristic_version.fullname()
                alert.details = response.parameters[0]
            else:
                alert.message = "Failed to check the heuristic '%s'" % job.server_job.heuristic_version.fullname()
                alert.details = "Unknown response from the Compilation Server. Expected: ANALYZE_OK, got: %s" % response.toString()

            job.outStream.write("ERROR - %s\n%s\n" % (alert.message, alert.details))

            job.test_status.heuristic_version.status = HeuristicVersion.STATUS_DISABLED
            job.test_status.heuristic_version.status_date = datetime.now()
            job.test_status.heuristic_version.save()

            job.test_status.error = True
            job.test_status.details = '%s\n%s' % (alert.message, alert.details)
            job.test_status.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            job.markAsFailed(alert=alert)
            return

        job.outStream.write("Analysis OK\n")

        # Enter the 'Test' phase
        job.test_status.phase = HeuristicTestStatus.PHASE_TEST
        job.test_status.save()

        job.operation = HeuristicChecker.processTestResult


    #---------------------------------------------------------------------------
    # Process the result of the test of the heuristic version
    #---------------------------------------------------------------------------
    def processTestResult(self, job):
        response = job.client.waitResponse()
        if response.name != 'TEST_OK':
            alert = Alert()
            error_report = None

            if response.name == 'TEST_ERROR':
                error_report = PluginErrorReport()
                error_report.heuristic_version = job.server_job.heuristic_version
                error_report.error_type = PluginErrorReport.ERROR_OTHER
                error_report.description = response.parameters[0]
            elif response.name == 'HEURISTIC_CRASH':
                error_report = PluginErrorReport()
                error_report.heuristic_version = job.server_job.heuristic_version
                error_report.error_type = PluginErrorReport.ERROR_CRASH
            elif response.name == 'HEURISTIC_TIMEOUT':
                error_report = PluginErrorReport()
                error_report.heuristic_version = job.server_job.heuristic_version
                error_report.error_type = PluginErrorReport.ERROR_TIMEOUT
            else:
                alert.details = "Unknown response from the Compilation Server. Expected: TEST_OK, got: %s" % response.toString()

            if error_report is not None:
                # Retrieve the context
                response = job.client.waitResponse()
                if response.name == 'CONTEXT':
                    error_report.context = response.parameters[0]

                # Retrieve the stack trace
                if (error_report.error_type == PluginErrorReport.ERROR_CRASH) and (len(error_report.context) > 0):
                    response = job.client.waitResponse()
                    if response.name == 'STACKTRACE':
                        error_report.stacktrace = response.parameters[0]

            alert.message = "The test of the heuristic '%s' failed" % job.server_job.heuristic_version.fullname()
            job.outStream.write("ERROR - %s\n" % alert.message)

            if len(alert.details) > 0:
                job.outStream.write("%s\n" % alert.details)

            job.test_status.heuristic_version.status = HeuristicVersion.STATUS_DISABLED
            job.test_status.heuristic_version.status_date = datetime.now()
            job.test_status.heuristic_version.save()

            job.test_status.error = True
            job.test_status.details = '%s' % alert.message
            if len(alert.details) > 0:
                job.test_status.details += '%s' % alert.details
            job.test_status.save()

            job.server_job.logs = getServerLogs(job.client)
            job.server_job.save()

            if error_report is not None:
                error_report.save()
                job.mail_sent = error_report.send_mail()

            job.markAsFailed(alert=alert)
            return

        job.outStream.write("Test OK\n")

        job.client.sendCommand('DONE')
        job.client.close()
        del job.client
        job.client = None


        ###### The heuristic is OK, move it into the private space ######

        # Retrieve the heuristics repository and lock it
        heuristicsRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
        heuristicsRepo.lock()

        # Retrieve the upload repository and lock it
        uploadRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        uploadRepo.lock()

        try:
            heuristic_author = job.server_job.heuristic_version.heuristic.author
            
            if job.server_job.heuristic_version.version > 1:
                heuristic_filename = '%s_v%d.cpp' % (defaultfilters.slugify(job.server_job.heuristic_version.heuristic.name), job.server_job.heuristic_version.version)
            else:
                heuristic_filename = '%s.cpp' % defaultfilters.slugify(job.server_job.heuristic_version.heuristic.name)
            
            # Create the heuristics repository if necessary
            heuristicsRepo.createIfNotExists()

            # Retrieve the file from the upload repository
            blob = uploadRepo.repository().tree()[heuristic_author.username.lower()][job.server_job.heuristic_version.filename]

            # Create the user directory in the heuristics repository if necessary
            user_path = os.path.join(heuristicsRepo.fullpath(), heuristic_author.username.lower())
            if not(os.path.exists(user_path)):
                os.mkdir(user_path)

            # Save the file into the heuristics repository
            destination = open(os.path.join(user_path, heuristic_filename), 'w')
            destination.write(blob.data)
            destination.close()

            # Commit the new file in the heuristics repository
            heuristicsRepo.commitFile('%s/%s' % (heuristic_author.username.lower(), heuristic_filename),
                                      "Add heuristic '%s'" % job.server_job.heuristic_version.fullname(),
                                      settings.COMMIT_AUTHOR)

            # Remove the file from the upload repository
            uploadRepo.removeFile('%s/%s' % (heuristic_author.username.lower(), job.server_job.heuristic_version.filename),
                                  "File '%s' of user '%s' removed, to create the heuristic '%s'" %
                                  (job.server_job.heuristic_version.filename, heuristic_author.username, job.server_job.heuristic_version.fullname()),
                                  settings.COMMIT_AUTHOR)

            # If the upload repository is empty, destroy it (no need to keep an history of the uploaded files)
            if not(uploadRepo.repository().tree().values()):
                uploadRepo.delete()

            # Modify the infos about the heuristic version in the database
            job.server_job.heuristic_version.filename = heuristic_filename
            job.server_job.heuristic_version.save()

        except:
            # Release the locks
            uploadRepo.unlock()
            heuristicsRepo.unlock()

            alert = Alert()
            alert.message = "Error while moving the heuristic version '%s' from the 'upload' repository to the 'heuristics' one" % job.server_job.heuristic_version.fullname()
            alert.details = traceback.format_exc()

            job.outStream.write("ERROR - %s\n%s\n" % (alert.message, alert.details))

            job.test_status.error = True
            job.test_status.details = '%s\n%s' % (alert.message, alert.details)
            job.test_status.save()

            job.markAsFailed(alert=alert)
            return

        # Release the locks
        uploadRepo.unlock()
        heuristicsRepo.unlock()

        # Mark the heuristic version as checked
        job.server_job.heuristic_version.checked = True
        job.server_job.heuristic_version.save()

        job.test_status.delete()

        # Mark the job as done
        job.markAsDone()
        
        # Send an event about the end of the test
        self.channel.sendMessage(Message('EVT_HEURISTIC_CHECKED', [job.server_job.heuristic_version.id]))


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):

        # Retrieve the list of heuristic versions not yet checked
        heuristic_versions = HeuristicVersion.objects.filter(checked=False, status=HeuristicVersion.STATUS_OK)
        
        for heuristic_version in heuristic_versions:
            # Delete the test status (if any)
            try:
                heuristic_version.test_status.delete()
            except:
                pass
            
            # Schedule the job
            self.jobs.addJob(command=Message('CHECK_HEURISTIC', [heuristic_version.id]))



def tasks():
    return [HeuristicChecker]

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
from pymash import Client
from pymash import Message
from servers.models import Server
from servers.models import Alert


#-------------------------------------------------------------------------------
# This task tries to identify the type of a server
#-------------------------------------------------------------------------------
class ServerIdentificator(Task):

    SUPPORTED_COMMANDS = { 'IDENTIFY_SERVER': [int] }   # <server_id>
    SUPPORTED_EVENTS   = {}


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        # Retrieve the server
        try:
            server = Server.objects.get(id=job.command.parameters[0])
        except:
            alert = Alert()
            alert.message = 'Unknown server ID: %d' % job.command.parameters[0]
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return
        
        # Mark the job as running
        job.outStream.write("Identification of the server '%s' at '%s:%d'...\n" % \
                                    (server.name, server.address, server.port))
        job.markAsRunning(server=server)

        # Establish a connection with the server
        job.client = Client(job.outStream)
        if not(job.client.connect(server.address, server.port)):
            job.outStream.write("ERROR - Failed to establish a connection with the server\n")
            job.markAsDelayed(60)
            return

        # Retrieve the type of the server
        job.client.sendCommand('INFO')

        job.operation = ServerIdentificator.processServerInfo


    #---------------------------------------------------------------------------
    # Process the response to the 'INFO' command
    #---------------------------------------------------------------------------
    def processServerInfo(self, job):
        
        # Retrieve the type of the server
        response = job.client.waitResponse()
        if (response.name != 'TYPE') or (len(response.parameters) != 1):
            alert = Alert()
            alert.message = 'Unexpected response from the server: %s' % response.toString()
            job.outStream.write("ERROR - %s\n" % alert.message)
            job.markAsFailed(alert=alert)
            return

        # Experiments Server
        if response.parameters[0] == 'ExperimentServer':
            job.outStream.write("--> Experiment Server\n")
            job.server_job.server.server_type = Server.EXPERIMENTS_SERVER
            job.server_job.server.save()

        # Compilation Server
        elif response.parameters[0] == 'CompilationServer':
            job.outStream.write("--> Compilation Server\n")
            job.server_job.server.server_type = Server.COMPILATION_SERVER
            job.server_job.server.save()

        # Clustering Server
        elif response.parameters[0] == 'ClusteringServer':
            job.outStream.write("--> Clustering Server\n")
            job.server_job.server.server_type = Server.CLUSTERING_SERVER
            job.server_job.server.save()

        # Debugging Server
        elif response.parameters[0] == 'DebuggingServer':
            job.outStream.write("--> Debugging Server\n")
            job.server_job.server.server_type = Server.DEBUGGING_SERVER
            job.server_job.server.save()

        # Application Server
        elif response.parameters[0] == 'ApplicationServer':
            # Read the media type
            response = job.client.waitResponse()
            if (response.name != 'SUBTYPE') or (len(response.parameters) != 1):
                alert = Alert()
                alert.message = 'Unexpected response from the application server: %s' % response.toString()
                job.outStream.write("ERROR - %s\n" % alert.message)
                job.markAsFailed(alert=alert)
                return

            # Images
            if response.parameters[0] == 'Images':
                job.outStream.write("--> Application Server, subtype = Images\n")
                job.server_job.server.server_type = Server.APPLICATION_SERVER
                job.server_job.server.subtype = Server.SUBTYPE_IMAGES
                job.server_job.server.save()

            # Interactive
            elif response.parameters[0] == 'Interactive':
                job.outStream.write("--> Application Server, subtype = Interactive\n")
                job.server_job.server.server_type = Server.APPLICATION_SERVER
                job.server_job.server.subtype = Server.SUBTYPE_INTERACTIVE
                job.server_job.server.save()

            # Unknown media type
            else:
                job.outStream.write("--> Application Server, media = Unknown\n")
                job.server_job.server.server_type = Server.APPLICATION_SERVER
                job.server_job.server.subtype = Server.SUBTYPE_NONE
                job.server_job.server.save()
        
        # Unknown server type
        else:
            job.outStream.write("--> Unknown\n")
            job.server_job.server.server_type = Server.UNKNOWN_SERVER
            job.server_job.server.save()

        job.client.sendCommand('DONE')

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):

        # Retrieve the list of unidentified servers
        servers = Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER)
        
        for server in servers:
            self.jobs.addJob(command=Message('IDENTIFY_SERVER', [server.id]))



def tasks():
    return [ServerIdentificator]

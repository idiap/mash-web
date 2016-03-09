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
from servers.models import Server
from datetime import datetime
from datetime import timedelta


#-------------------------------------------------------------------------------
# This task checks the status of the servers found in the database
#-------------------------------------------------------------------------------
class ServersChecker(Task):

    SUPPORTED_COMMANDS = { 'CHECK_SERVERS_STATUS': [] }
    SUPPORTED_EVENTS   = {}


    #---------------------------------------------------------------------------
    # Constructor
    #
    # @param channel    The channel to use to receive and send messages
    #---------------------------------------------------------------------------
    def __init__(self):
        super(ServersChecker, self).__init__()
        self.last_check = None


    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):

        # Retrieve the list of servers
        servers = Server.objects.all()

        # Check the status of each server
        for server in servers:
            server.status = Server.SERVER_STATUS_UNKNOWN
            server.save()

            job.outStream.write("Attempt to connect to server '%s' at '%s:%d'... " % \
                                 (server.name, server.address, server.port))

            client = Client()

            if client.connect(server.address, server.port):
                job.outStream.write("ONLINE\n")
                server.status = Server.SERVER_STATUS_ONLINE
            else:
                job.outStream.write("OFFLINE\n")
                server.status = Server.SERVER_STATUS_OFFLINE

            client.close()

            server.save()

        self.last_check = datetime.now()

        job.markAsDone()


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        self.jobs.addJob(command='CHECK_SERVERS_STATUS')


    #---------------------------------------------------------------------------
    # Called when a new command was received. It allows the task to process it
    # independently of the jobs mechanism.
    #
    # @param    command     The command
    # @return               'False' if the command must be handled by the
    #                       standard jobs mechanism
    #---------------------------------------------------------------------------
    def onCommandReceived(self, command):
        if self.jobs.count() > 0:
            return True
        
        current_time = datetime.now()
        delta = timedelta(seconds=2)

        return (self.last_check is not None) and (current_time <= self.last_check + delta)



def tasks():
    return [ServersChecker]

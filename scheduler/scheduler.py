#! /usr/bin/env python  

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


################################################################################
#                                                                              #
# Scheduler                                                                    #
#                                                                              #
# The Scheduler is the link between the website and the various MASH servers   #
# (Experiment Server, Compilation Server, Application Servers, ...).           #
#                                                                              #
################################################################################

import website
from django.conf import settings
from django.db.models import Q
from scheduler_listener import SchedulerListener
from scheduler_listener import PROTOCOL
from tasks.task import Task
from pymash import OutStream
from pymash import CommunicationChannel
from pymash import ThreadedServer
from mash.servers.models import Job as ServerJob
import sys
import os
import select
import signal
import glob
import traceback
from datetime import datetime
from datetime import timedelta
from optparse import OptionParser


def term_signal_handler(signum, frame):
    raise KeyboardInterrupt


############################### SCHEDULER CLASS ################################

#-------------------------------------------------------------------------------
# Represents the scheduler
#-------------------------------------------------------------------------------
class Scheduler:

    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self):
        self.server         = None
        self.input_channel  = None
        self.tasks          = []

        self.outStream = OutStream()
        self.outStream.open('Scheduler', 'logs/scheduler-$TIMESTAMP.log')


    #---------------------------------------------------------------------------
    # Start the scheduling
    #---------------------------------------------------------------------------
    def start(self):

        # Signal handling
        signal.signal(signal.SIGTERM, term_signal_handler)

        # Setup the server
        (SchedulerListener.OUTPUT_CHANNEL, self.input_channel) = CommunicationChannel.create(CommunicationChannel.CHANNEL_TYPE_SIMPLEX)
        self.server = ThreadedServer(settings.SCHEDULER_ADDRESS, settings.SCHEDULER_PORT, SchedulerListener)
        self.server.start()

        # Create the tasks
        files = glob.glob('implemented_tasks/*.py')
        for inFile in files:
            try:
                self.outStream.write("Loading tasks from '%s'\n" % inFile)

                name = inFile[:-3].replace('/', '.')
                module = __import__(name)
        
                parts = name.split('.')
                for part in parts[1:]:
                    module = module.__getattribute__(part)

                if hasattr(module, 'tasks'):
                    for task_class in module.tasks():
                        self.tasks.append(task_class())

                        self.outStream.write("    Supported commands:\n")
                        for command, parameters in task_class.SUPPORTED_COMMANDS.items():
                            self.outStream.write("        - %s\n" % command)
                            SchedulerListener.addCommand(command, len(parameters))
                        
            except Exception, e:
                previous = OutStream.outputToConsole
                OutStream.outputToConsole = True

                self.outStream.write("Failed to load the tasks defined in '%s', reason:\n" % inFile)
                self.outStream.write('ERROR: %s\n' % str(e))
                self.outStream.write(traceback.format_exc() + '\n')

                OutStream.outputToConsole = previous
                
        try:
            # Remove all the delayed and running jobs from the database, and simulate
            # a reception of their commands to reschedule them
            jobs = ServerJob.objects.filter(Q(status=ServerJob.STATUS_DELAYED) | Q(status=ServerJob.STATUS_RUNNING))
            for job in jobs:
                SchedulerListener.OUTPUT_CHANNEL.sendMessage(job.command)
            jobs.delete()

            # Start the tasks
            for task in self.tasks:
                task.start()

            start_time = datetime.now()
            start = datetime.now()

            while (True):
                current_time = datetime.now()
                delta = timedelta(days=1)
                if current_time > start_time + delta:
                    start_time = current_time
                    self.outStream.write('----------------------------------------------------------------\n')
                    self.outStream.write('Opening a new log file...\n')
                    self.outStream.close()
                    self.outStream = OutStream()
                    self.outStream.open('Scheduler', 'logs/scheduler-$TIMESTAMP.log')

                # Build the list of file descriptors we must listen to
                tasks_file_descriptors = []
                for task_file_descriptors in [ task.getFileDescriptors() for task in self.tasks ]:
                    tasks_file_descriptors.extend(task_file_descriptors)

                select_list = [self.input_channel.readPipe]
                select_list.extend(tasks_file_descriptors)

                # Compute the timeout
                timeouts = filter(lambda x: x is not None, map(lambda x: x.getTimeout(), self.tasks))
                timeout = None
                if len(timeouts) > 0:
                    timeout = reduce(lambda x, y: min(x, y), timeouts)

                # Wait for a message
                if timeout is None:
                    self.outStream.write('Waiting for an event, no timeout...\n')
                else:
                    self.outStream.write('Waiting for an event, with a timeout of %d seconds...\n' % timeout)
                
                ready_to_read, ready_to_write, in_error = select.select(select_list, [], select_list, timeout)

                # Tell the tasks about the event
                end = datetime.now()
                elapsed = (end - start).seconds
                for task in self.tasks:
                    task.onEvent(elapsed, ready_to_read)

                if elapsed > 0:
                    start = end

                channels_to_read = []

                # Commands sent by the clients
                if self.input_channel.readPipe in ready_to_read:
                    channels_to_read.append(self.input_channel)

                # Commands and events sent by the tasks
                ready_tasks_file_descriptors = filter(lambda x: x in tasks_file_descriptors, ready_to_read)
                for channels in [ filter(lambda x: x.readPipe == file_descriptor, map(lambda x: x.out_channel, self.tasks)) for file_descriptor in ready_tasks_file_descriptors ]:
                    channels_to_read.extend(channels)

                # Process all the commands and events received via channels
                for channel in channels_to_read:
                    while (True):
                        message = channel.waitMessage(block=False)
                        if message is None:
                            break

                        self.outStream.write('Got message: %s\n' % message.toString())

                        # Find the task that is able to handle it
                        for task in self.tasks:
                            if task.processMessage(message):
                                break
                
                # Run the jobs that were scheduled
                for task in self.tasks:
                    task.processNewJobs()

        except KeyboardInterrupt:
            self.outStream.write("Scheduler stopped\n")

        for task in self.tasks:
            task.stop()

        self.server.stop()
        self.input_channel.close()
        
        return True


##################################### MAIN #####################################

if __name__ == "__main__":

    print """********************************************************************************
* Scheduler
* Protocol: %s
********************************************************************************
""" % PROTOCOL

    # Setup of the command-line arguments parser
    usage = "Usage: %prog [options]"
    parser = OptionParser(usage, version="%prog 2.0")
    parser.add_option("--verbose", action="store_true", default=False,
                      dest="verbose", help="Verbose mode")

    # Handling of the arguments
    (options, args) = parser.parse_args()

    OutStream.outputToConsole = options.verbose
    
    # Start the scheduling
    scheduler = Scheduler()
    scheduler.start()

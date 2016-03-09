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
from django.core.mail import send_mail
from pymash import Client
from pymash import OutStream
from pymash import CommunicationChannel
from pymash import Message
from tasks.jobs import JobList
from tasks.jobs import Job
from utilities.logs import saveLogFile
from mash.servers.models import Job as ServerJob
from mash.servers.models import Alert
from datetime import datetime
from datetime import timedelta
import os
import string
import traceback


#-------------------------------------------------------------------------------
# Represents a task, responsible to perform jobs of a particular type
#-------------------------------------------------------------------------------
class Task(object):
    
    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self):
        (self.channel, self.out_channel) = CommunicationChannel.create(
                                                CommunicationChannel.CHANNEL_TYPE_SIMPLEX)

        self.start_time  = datetime.now()
        self.jobs        = JobList()
        self.new_jobs    = []
        self.nb_max_jobs = 20
        self.outStream   = OutStream()
        
        self.outStream.open('Task %s' % self.__class__.__name__,
                            'logs/task-%s-$TIMESTAMP.log' % self.__class__.__name__.lower())


    #---------------------------------------------------------------------------
    # Destructor
    #---------------------------------------------------------------------------
    def __del__(self):
        self.channel.close()
        self.out_channel.close()
        self.outStream.close()


    #---------------------------------------------------------------------------
    # Start the task
    #---------------------------------------------------------------------------
    def start(self):
        self.outStream.write('Start the processing...\n')
        self.onStartup()

        # Attempt to run the jobs that were added by the 'onStartup()' method
        for job in self.jobs.getJobs(status=ServerJob.STATUS_SCHEDULED):
            self._processJob(job)

    
    #---------------------------------------------------------------------------
    # Stop the task
    #---------------------------------------------------------------------------
    def stop(self):
        for job in self.jobs.getJobs(status=ServerJob.STATUS_RUNNING):
            job.markAsScheduled()

    
    #---------------------------------------------------------------------------
    # Retrieve the maximum time to wait for an event for this task
    #---------------------------------------------------------------------------
    def getTimeout(self):
        timeout = self.jobs.getNextTimeout()
        if (timeout is None) and (self.jobs.count(ServerJob.STATUS_SCHEDULED) > 0):
            timeout = 60
        
        return timeout

    
    #---------------------------------------------------------------------------
    # Retrieve the list of file descriptors that we must listen to for this task
    #---------------------------------------------------------------------------
    def getFileDescriptors(self):
        file_descriptors = [self.out_channel.readPipe]

        running_jobs = filter(lambda x: x.client is not None, self.jobs.getJobs(ServerJob.STATUS_RUNNING))
        file_descriptors.extend(map(lambda x: x.client.socket, running_jobs))
        
        return file_descriptors
    
    
    #---------------------------------------------------------------------------
    # Called when an event happened on one of the file descriptors reported by
    # getFileDescriptors(), or in case of timeout
    #---------------------------------------------------------------------------
    def onEvent(self, elapsed, ready_to_read):
        
        # Create a new log file per day
        current_time = datetime.now()
        delta = timedelta(days=1)
        if current_time > self.start_time + delta:
            self.start_time = current_time
            self.outStream.write('----------------------------------------------------------------\n')
            self.outStream.write('Opening a new log file...\n')
            self.outStream.close()
            self.outStream = OutStream()
            self.outStream.open('Task %s' % self.__class__.__name__,
                                'logs/task-%s-$TIMESTAMP.log' % self.__class__.__name__.lower())

        # Process the elapsed time
        if elapsed > 0:
            jobs = self.jobs.updateTimeouts(elapsed)
            for index, job in enumerate(jobs):
                if index == 0:
                    self.outStream.write('Timeout!\n')
                self._processJob(job)

        # Process the responses from the clients of the running jobs
        nb_jobs_done = 0
        running_jobs = filter(lambda x: x.client is not None, self.jobs.getJobs(ServerJob.STATUS_RUNNING))
        jobs = filter(lambda x: x.client.socket in ready_to_read, running_jobs)
        for job in jobs:
            while True:
                self._processJob(job)
                if (job.server_job.status == ServerJob.STATUS_DONE) or \
                   (job.server_job.status == ServerJob.STATUS_FAILED):
                    nb_jobs_done += 1
                    break

                if not(job.client.hasResponse()):
                    break

        # Attempt to run as many currently scheduled jobs as just finished
        nb_max_jobs = nb_jobs_done
        nb_jobs_running = 0
        jobs = self.jobs.getJobs(ServerJob.STATUS_SCHEDULED)
        for job in jobs:
            self._processJob(job)
            if job.server_job.status == ServerJob.STATUS_RUNNING:
                nb_jobs_running += 1
                if nb_jobs_running == nb_max_jobs:
                    break


    #---------------------------------------------------------------------------
    # Ask the task to handle the provided message
    #
    # @param    message     The message
    # @return               A boolean indicating if the task is handling the
    #                       message
    #---------------------------------------------------------------------------
    def processMessage(self, message):

        # Check if the task can handle the message
        if not(isinstance(message, Message)):
            message = Message.fromString(message)
                
        if not(message.name in self.SUPPORTED_COMMANDS) and \
           not(message.name in self.SUPPORTED_EVENTS):
            return False

        # Check that the format of the message is correct
        format = self.dataFormat(message.name)
        
        parameters = message.parameters
        if parameters is None:
            parameters = []

        if len(format) != len(parameters):
            self.outStream.write('ERROR: Invalid number of arguments, expected %d, ' \
                                 'got message: %s\n' % (len(format), message.toString()))
            return False

        try:
            if message.parameters is not None:
                message.parameters = map(lambda (index, value): format[index](value), enumerate(message.parameters))
        except:
            self.outStream.write("ERROR: Invalid type of arguments, expected '%s', " \
                                 "got message: %s\n" % (str(format), message.toString()))
            return False

        # Determine if the message is a command or an event
        try:
            if self.isCommand(message.name):
                self.outStream.write('Got command: %s\n' % message.toString())

                self.outStream.write('Trying task-specific handling...\n')
                if not(self.onCommandReceived(message)):
                    self.outStream.write('Add a job in the list...\n')
                    job = self.jobs.addJob(command=message)
                    self.new_jobs.append(job)
            else:
                self.outStream.write('Got event: %s\n' % message.toString())
                jobs = self.onEventReceived(message)
                if jobs is not None:
                    for job in jobs:
                        self.new_jobs.append(job)
        except:
            self.outStream.write('Exception during the preparation of a job:\n')
            details = traceback.format_exc()
            self.outStream.write(details + "\n")

            subject = '[MASH ALERT] Exception during the preparation of a job'
            content = 'Message: %s\n\n%s' % (message.toString(), details)

            try:
                send_mail(subject, content, settings.DEFAULT_FROM_EMAIL,
                          [ admin[1] for admin in settings.ADMINS ])
            except:
                pass

        return True


    #---------------------------------------------------------------------------
    # Attempt to run the jobs that were scheduled
    #---------------------------------------------------------------------------
    def processNewJobs(self):
        for job in self.new_jobs:
            self._processJob(job)

        self.new_jobs = []


    #---------------------------------------------------------------------------
    # Start or continue a job
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def _processJob(self, job):

        if self.jobs.count(ServerJob.STATUS_RUNNING) >= self.nb_max_jobs:
            return        

        self.outStream.write("Processing of the job #%d: '%s'\n" % (job.server_job.id, job.command.toString()))

        # Job-specific processing
        try:
            if job.operation is None:
                job.operation = self.__class__.process

            self.outStream.write("    Current operation: '%s'\n" % (job.operation.__name__))
            job.outStream.write("Current operation: '%s'\n" % (job.operation.__name__))

            job.operation(self, job)
        except:
            self.outStream.write('Exception during the processing of the job:\n')
            message = traceback.format_exc()
            self.outStream.write(message + "\n")

            alert = Alert()
            alert.message = 'Exception during the processing of the job'
            alert.details = message

            job.markAsFailed(alert=alert)

            subject = '[MASH ALERT] Exception during the processing of a job'
            message = 'Job ID: %d\nCommand: %s\n\n%s' % (job.server_job.id, job.command.toString(), message)

            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                          [ admin[1] for admin in settings.ADMINS ])
            except:
                pass

            return

        
        # Process the (possibly new) status of the job
        if job.server_job.status == ServerJob.STATUS_SCHEDULED:
            self.outStream.write('Result: the job is still scheduled\n')
            self.jobs.rescheduleJob(job)

        elif job.server_job.status == ServerJob.STATUS_RUNNING:
            self.outStream.write('Result: the job is still running\n')

        elif job.server_job.status == ServerJob.STATUS_DELAYED:
            self.outStream.write('Result: the job was delayed for %d seconds\n' % job.timeout)

        elif job.server_job.status == ServerJob.STATUS_DONE:
            self.outStream.write('Result: the job is done\n')
            self.jobs.removeJobs(job)
            del job

        elif job.server_job.status == ServerJob.STATUS_FAILED:
            self.outStream.write('Result: the job has failed\n')
            self.jobs.removeJobs(job)

            alert = job.alert()
            if alert is not None:

                # Dump the output stream of the task in a log file
                if job.server_job.logs is not None:
                    saveLogFile(job.server_job.logs, '%s.log' % self.__class__.__name__, self.outStream.dump())

                # If not already done, send a mail to the administrators about the problem
                if not(job.mail_sent):
                    subject = '[MASH ALERT] ' + alert.message

                    message = ''
                    if alert.details is not None:
                        message = alert.details + '\n\n'

                    message += 'Job ID: %d\nCommand: %s\n' % (job.server_job.id, job.command.toString())

                    if job.server_job.heuristic_version is not None:
                        message += 'Heuristic version: %s/heuristics/v%d/\n' % (settings.SECURED_WEBSITE_URL_DOMAIN, job.server_job.heuristic_version.id)

                    if job.server_job.experiment is not None:
                        message += 'Experiment: %s/experiments/%d/\n' % (settings.SECURED_WEBSITE_URL_DOMAIN, job.server_job.experiment.id)

                    if job.server_job.logs is not None:
                        for log_file in job.server_job.logs.files.all():
                            try:
                                message += '\n\n' + '-' * 80 + '\n'
                                message += log_file.file

                                in_file = open(os.path.join(settings.LOG_FILES_ROOT, job.server_job.logs.folder, log_file.file), 'r')
                                in_file.seek(0, os.SEEK_END)

                                size = in_file.tell()

                                if size > 10 * 1024:
                                    message += ' (truncated)'
                                    in_file.seek(-10 * 1024, os.SEEK_END)
                                else:
                                    in_file.seek(0, os.SEEK_SET)

                                message += '\n\n'

                                if size > 10 * 1024:
                                    content = in_file.read(10 * 1024)
                                    message += '...\n' + content
                                else:
                                    content = in_file.read()
                                    message += content

                                in_file.close()
                            except:
                                pass

                        try:
                            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                                      [ admin[1] for admin in settings.ADMINS ])
                        except:
                            pass

            del job


    #_____ Methods to implement __________

    #---------------------------------------------------------------------------
    # Starts the job-specific processing
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def process(self, job):
        pass


    #---------------------------------------------------------------------------
    # Method called at startup. Use it to look in the database if there is some
    # job already waiting. They must be put in the job list.
    #---------------------------------------------------------------------------
    def onStartup(self):
        pass


    #---------------------------------------------------------------------------
    # Called when a new command was received. It allows the task to process it
    # independently of the jobs mechanism.
    #
    # @param    command     The command
    # @return               'False' if the command must be handled by the
    #                       standard jobs mechanism
    #---------------------------------------------------------------------------
    def onCommandReceived(self, command):
        return False


    #---------------------------------------------------------------------------
    # Called when a new event was received
    #
    # @param event  The event
    # @return       None, or a list of new jobs (already in the jobs list)
    #---------------------------------------------------------------------------
    def onEventReceived(self, event):
        return None


    #_____ Utility methods __________

    #---------------------------------------------------------------------------
    # Class method used by the task to know the format of the parameters it must
    # accept for a specific command or event
    #
    # @return   An array of the following form: [type1, type2, ..., typeN], with
    #           N being the number of parameters
    #---------------------------------------------------------------------------
    @classmethod
    def dataFormat(cls, command_name):
        if command_name in cls.SUPPORTED_COMMANDS:
            return cls.SUPPORTED_COMMANDS[command_name]

        if command_name in cls.SUPPORTED_EVENTS:
            return cls.SUPPORTED_EVENTS[command_name]

        return None


    #---------------------------------------------------------------------------
    # Class method used indicating if a given message name corresponds to a
    # command or an event
    #---------------------------------------------------------------------------
    @classmethod
    def isCommand(cls, message_name):
        return (message_name in cls.SUPPORTED_COMMANDS.keys())

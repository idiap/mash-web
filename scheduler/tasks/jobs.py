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


from pymash.messages import Message
from pymash.outstream import OutStream
from mash.servers.models import Job as ServerJob
from mash.experiments.models import Experiment
from utilities.logs import saveLogFile


#-------------------------------------------------------------------------------
# Holds all the informations about a job of a task
#
# Can be subclassed to add more informations if needed
#-------------------------------------------------------------------------------
class Job(object):

    #---------------------------------------------------------------------------
    # Constructor
    #
    # @param server_job     Job model instance
    # @param command        Command executed by the job
    #
    # Both parameters are mutually exclusive
    #---------------------------------------------------------------------------
    def __init__(self, server_job=None, command=None):
        
        if server_job is not None:
            self.server_job = server_job
            self.command    = Message.fromString(server_job.command)

        elif command is not None:
            if not(isinstance(command, Message)):
                command = Message.fromString(command)

            self.command = command
            
            self.server_job         = ServerJob()
            self.server_job.command = command.toString()
            self.server_job.status  = ServerJob.STATUS_SCHEDULED
            self.server_job.save()
        
        else:
            raise ValueError()
        
        self.timeout    = None          # Timeout for the job (if delayed, in seconds)
        self.client     = None          # Network client object used by the job
        self.operation  = None          # Current operation (task-specific)
        self.mail_sent  = False         # Indicates if a mail was sent about the errors
        self.outStream  = OutStream()   # Output stream relative to this job

    #---------------------------------------------------------------------------
    # Destructor
    #---------------------------------------------------------------------------
    def __del__(self):
        self.outStream.close()

    #---------------------------------------------------------------------------
    # Mark the job as scheduled
    #
    # @param server     The server currently executing the job
    #---------------------------------------------------------------------------
    def markAsScheduled(self):
        self.server_job.status = ServerJob.STATUS_SCHEDULED
        self.server_job.server = None
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = Experiment.STATUS_SCHEDULED
            self.server_job.experiment.save()
            self.server_job.experiment.notifications.all().delete()

        self.timeout = None
        self.operation = None

        if self.client is not None:
            self.client.sendCommand('DONE')
            self.client.close()
            del self.client
            self.client = None

        self.outStream.delete()
        self.outStream = OutStream()

    #---------------------------------------------------------------------------
    # Mark the job as running
    #
    # @param server             The server currently executing the job
    # @param heuristic_version  The heuristic version related to the job
    # @param experiment         The experiment related to the job
    #---------------------------------------------------------------------------
    def markAsRunning(self, server=None, heuristic_version=None, experiment=None):
        self.server_job.status = ServerJob.STATUS_RUNNING
        self.server_job.server = server
        self.server_job.heuristic_version = heuristic_version
        self.server_job.experiment = experiment
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = Experiment.STATUS_RUNNING
            self.server_job.experiment.save()

        self.timeout = None

        self.outStream.open('Job %d' % self.server_job.id,
                            'logs/task-%s-job-%d.log' % (self.__class__.__name__.lower(), self.server_job.id))

        self.outStream.write('Executing command: %s\n' % self.server_job.command)

    #---------------------------------------------------------------------------
    # Mark the job as done
    #---------------------------------------------------------------------------
    def markAsDone(self, experiment_status=Experiment.STATUS_DONE):
        self.server_job.status = ServerJob.STATUS_DONE
        self.server_job.server = None
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = experiment_status
            self.server_job.experiment.save()
            self.server_job.experiment.notifications.all().delete()

        self.operation = None
        
        if self.client is not None:
            self.client.sendCommand('DONE')
            self.client.close()
            del self.client
            self.client = None

        self.outStream.delete()
        self.outStream = OutStream()

    #---------------------------------------------------------------------------
    # Mark the job as failed
    #
    # @param alert  The alert explaining the problem
    #---------------------------------------------------------------------------
    def markAsFailed(self, alert=None):
        self.server_job.status = ServerJob.STATUS_FAILED
        self.server_job.server = None
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = Experiment.STATUS_FAILED
            self.server_job.experiment.save()
            self.server_job.experiment.notifications.all().delete()

        self.operation = None

        if alert is not None:
            alert.job = self.server_job
            alert.save()
        
        if self.client is not None:
            self.client.sendCommand('DONE')
            self.client.close()
            del self.client
            self.client = None

        if self.server_job.logs is not None:
            content = self.outStream.dump(200 * 1024)
            if content is not None:
                saveLogFile(self.server_job.logs, 'Job.log', content)

        self.outStream.delete()
        self.outStream = OutStream()

    #---------------------------------------------------------------------------
    # Mark the job as cancelled
    #---------------------------------------------------------------------------
    def markAsCancelled(self):
        self.server_job.status = ServerJob.STATUS_CANCELLED
        self.server_job.server = None
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = Experiment.STATUS_FAILED
            self.server_job.experiment.save()
            self.server_job.experiment.notifications.all().delete()

        self.operation = None

        if self.client is not None:
            self.client.sendCommand('DONE')
            self.client.close()
            del self.client
            self.client = None

        self.outStream.delete()
        self.outStream = OutStream()

    #---------------------------------------------------------------------------
    # Mark the job as delayed
    #
    # @param delay  The delay
    #---------------------------------------------------------------------------
    def markAsDelayed(self, delay):
        self.server_job.status = ServerJob.STATUS_DELAYED
        self.server_job.server = None
        self.server_job.save()

        if self.server_job.experiment is not None:
            self.server_job.experiment.status = Experiment.STATUS_SCHEDULED
            self.server_job.experiment.save()
            self.server_job.experiment.notifications.all().delete()

        self.timeout = delay
        self.operation = None
        
        if self.client is not None:
            self.client.sendCommand('DONE')
            self.client.close()
            del self.client
            self.client = None

        self.outStream.delete()
        self.outStream = OutStream()

    #---------------------------------------------------------------------------
    # Return the alert associated to the job (if any)
    #---------------------------------------------------------------------------
    def alert(self):
        try:
            return self.server_job.alert
        except:
            return None


#-------------------------------------------------------------------------------
# Holds a list of jobs
#-------------------------------------------------------------------------------
class JobList(object):

    #---------------------------------------------------------------------------
    # Constructor
    #
    # @param jobs_class     Class of the job instances
    #---------------------------------------------------------------------------
    def __init__(self, jobs_class=Job):
        self.jobs_class = jobs_class
        self.jobs = []

    #---------------------------------------------------------------------------
    # Returns the number of jobs in the list
    #
    # @param    status  (Optional) Only count the jobs with this status
    # @return           The number of jobs
    #---------------------------------------------------------------------------
    def count(self, status=None):
        return len(self.getJobs(status))

    #---------------------------------------------------------------------------
    # Indicates if a job of the list is already executing the given command
    #
    # @param    command     The command
    # @return               'True' if a job executes the command
    #---------------------------------------------------------------------------
    def hasJob(self, command):
        if not(isinstance(command, Message)):
            command = Message.fromString(command)

        return len(filter(lambda x: x.command.equals(command), self.jobs)) > 0

    #---------------------------------------------------------------------------
    # Add a new job to the list
    #
    # @param    server_job  Job model instance
    # @param    command     Command executed by the job
    # @return               The job
    #
    # Both parameters are mutually exclusive
    #---------------------------------------------------------------------------
    def addJob(self, server_job=None, command=None):
        job = self.jobs_class(server_job=server_job, command=command)
        self.jobs.append(job)
        return job

    #---------------------------------------------------------------------------
    # Returns a list of the jobs, optionally restricted to those with a
    # particular status and/or command
    #
    # @param    status  (Optional) The status
    # @param    command (Optional) The command
    # @return           The list of jobs
    #---------------------------------------------------------------------------
    def getJobs(self, status=None, command=None):
        result = self.jobs

        if status is not None:
            result = filter(lambda x: x.server_job.status == status, result)

        if command is not None:
            if not(isinstance(command, Message)):
                command = Message.fromString(command)

            result = filter(lambda x: x.command.equals(command), result)

        return result

    #---------------------------------------------------------------------------
    # Remove some jobs from the list
    #
    # @param jobs   One job, or an array of jobs
    #---------------------------------------------------------------------------
    def removeJobs(self, jobs):
        if isinstance(jobs, list):
            self.jobs = filter(lambda x: x not in jobs, self.jobs)
        else:
            self.jobs.remove(jobs)

    #---------------------------------------------------------------------------
    # Reschedule a job (put it at the end of the queue)
    #
    # @param job    The job
    #---------------------------------------------------------------------------
    def rescheduleJob(self, job):
        self.jobs.remove(job)
        self.jobs.append(job)

    #---------------------------------------------------------------------------
    # Returns the next timeout that must occurs
    #
    # @return   The next timeout, or None
    #---------------------------------------------------------------------------
    def getNextTimeout(self):
        jobs = self.getJobs(ServerJob.STATUS_DELAYED)
        if len(jobs) == 0:
            return None

        return reduce(lambda x, y: min(x, y), map(lambda x: x.timeout, jobs))

    #---------------------------------------------------------------------------
    # Update the timeouts of all the delayed jobs of the list, return a list of
    # the delayed jobs that must be executed again
    #
    # @param    elapsed     The number of seconds elapsed
    # @return               The delayed jobs that must be executed again
    #---------------------------------------------------------------------------
    def updateTimeouts(self, elapsed):
        delayed = self.getJobs(ServerJob.STATUS_DELAYED)
        for job in delayed:
            job.timeout -= elapsed
            if job.timeout <= 0:
                job.markAsScheduled()

        return filter(lambda x: x.server_job.status == ServerJob.STATUS_SCHEDULED, delayed)

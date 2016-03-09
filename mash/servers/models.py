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


from django.db import models
from mash.heuristics.models import HeuristicVersion
from mash.experiments.models import Experiment, Configuration
from mash.clustering.models import Algorithm
from logs.models import LogEntry
from mash.tasks.models import Task, Database, Goal


class Server(models.Model):

    UNKNOWN_SERVER      = 'UNKN'
    UNIDENTIFIED_SERVER = 'UNID'
    COMPILATION_SERVER  = 'COMP'
    EXPERIMENTS_SERVER  = 'EXPE'
    APPLICATION_SERVER  = 'APPL'
    CLUSTERING_SERVER   = 'CLUS'
    DEBUGGING_SERVER    = 'DEBG'

    SERVER_TYPES = (
        (UNKNOWN_SERVER,        'Unknown'),
        (UNIDENTIFIED_SERVER,   'Unidentified'),
        (COMPILATION_SERVER,    'CompilationServer'),
        (EXPERIMENTS_SERVER,    'ExperimentsServer'),
        (APPLICATION_SERVER,    'ApplicationServer'),
        (CLUSTERING_SERVER,     'ClusteringServer'),
        (DEBUGGING_SERVER,      'DebuggingServer'),
    )
    
    SUBTYPE_NONE        = 'NONE'
    SUBTYPE_IMAGES      = 'IMAG'
    SUBTYPE_INTERACTIVE = 'INTE'

    SUBTYPES = (
        (SUBTYPE_NONE,          'None'),
        (SUBTYPE_IMAGES,        'Images'),
        (SUBTYPE_INTERACTIVE,   'Interactive'),
    )

    SERVER_STATUS_UNKNOWN   = 'UNKN'
    SERVER_STATUS_ONLINE    = 'ON'
    SERVER_STATUS_OFFLINE   = 'OFF'

    SERVER_STATUS = (
        (SERVER_STATUS_UNKNOWN, 'Unknown'),
        (SERVER_STATUS_ONLINE,  'Online'),
        (SERVER_STATUS_OFFLINE, 'Offline'),
    )

    name                    = models.CharField(max_length=200)
    address                 = models.CharField(max_length=200)
    port                    = models.IntegerField()
    server_type             = models.CharField(max_length=4, choices=SERVER_TYPES, default=UNKNOWN_SERVER)
    subtype                 = models.CharField(max_length=4, choices=SUBTYPES, default=SUBTYPE_NONE)
    restrict_experiment     = models.CharField(max_length=4, null=True, blank=True, choices=Configuration.EXPERIMENT_TYPES)
    supported_tasks         = models.ManyToManyField(Task, related_name='servers', null=True, blank=True)
    provided_databases      = models.ManyToManyField(Database, related_name='servers', null=True, blank=True)
    provided_goals          = models.ManyToManyField(Goal, related_name='servers', null=True, blank=True)
    clustering_algorithm    = models.ForeignKey(Algorithm, related_name='servers', null=True, blank=True)
    status                  = models.CharField(max_length=4, choices=SERVER_STATUS,
                                               default=SERVER_STATUS_UNKNOWN)

    def __unicode__(self):
        return self.name

    def current_job(self):
        try:
            return self.jobs.filter(status=Job.STATUS_RUNNING).get()
        except:
            return None


class Job(models.Model):

    STATUS_SCHEDULED = 'SCH'
    STATUS_RUNNING   = 'RUN'
    STATUS_DONE      = 'DONE'
    STATUS_FAILED    = 'FAIL'
    STATUS_DELAYED   = 'DELY'
    STATUS_CANCELLED = 'CANC'

    JOB_STATUS = (
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_RUNNING,   'Running'),
        (STATUS_DONE,      'Done'),
        (STATUS_FAILED,    'Failed'),
        (STATUS_DELAYED,   'Delayed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    server              = models.ForeignKey(Server, null=True, blank=True, related_name='jobs')
    heuristic_version   = models.ForeignKey(HeuristicVersion, null=True, blank=True, related_name='job')
    experiment          = models.ForeignKey(Experiment, null=True, blank=True, related_name='job')
    status              = models.CharField(max_length=4, choices=JOB_STATUS, default=STATUS_SCHEDULED)
    command             = models.CharField(max_length=255, null=False, blank=False)
    logs                = models.OneToOneField(LogEntry, null=True, blank=True, related_name='job')


    def __unicode__(self):
        name = self.command

        try:
            if self.heuristic_version is not None:
                name += ", heuristic version = '%s'" % self.heuristic_version.fullname()
        except HeuristicVersion.DoesNotExist:
            name += ", heuristic version = <deleted>"

        try:
            if self.experiment is not None:
                name += ", experiment = '%s'" % self.experiment.fullname()
        except Experiment.DoesNotExist:
            name += ", experiment = <deleted>"
        
        return name


class Alert(models.Model):

    job     = models.OneToOneField(Job, related_name='alert')
    message = models.TextField(blank=True, )
    details = models.TextField(blank=True, )

    def __unicode__(self):
        try:
            return u"Alert for job '%s'" % self.job
        except:
            return self.message

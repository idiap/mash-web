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
from experiments.models import Experiment, Configuration
from heuristics.models import HeuristicVersion


class FactoryTask(models.Model):

    config         = models.ForeignKey(Configuration,blank=True)
    taskNumber     = models.IntegerField()
    description    = models.TextField(blank=True)
    imageName      = models.TextField(blank=True)

    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        return 'Task%s' % self.taskNumber



class FactoryTaskResult(models.Model):

    task       = models.ForeignKey(FactoryTask)
    experiment = models.ForeignKey(Experiment, blank=True)
    obsolete   = models.BooleanField(default=False)



class DebuggingEntry(models.Model):

    STATUS_SCHEDULED    = 'SCH'
    STATUS_RUNNING      = 'RUN'
    STATUS_DONE         = 'DONE'
    STATUS_FAILED       = 'FAIL'

    STATUS = (
        (STATUS_SCHEDULED,  'Scheduled'),
        (STATUS_RUNNING,    'In progress'),
        (STATUS_DONE,       'Done'),
        (STATUS_FAILED,     'Failed'),
    )

    STATUS_TEXTS = {
        STATUS_SCHEDULED:   'Scheduled',
        STATUS_RUNNING:     'In progress',
        STATUS_DONE:        'Done',
        STATUS_FAILED:      'Failed',
    }

    task                = models.ForeignKey(FactoryTask)
    sequence            = models.IntegerField(default=0)
    start_frame         = models.IntegerField(default=-1)
    end_frame           = models.IntegerField(default=-1)
    heuristic_version   = models.OneToOneField(HeuristicVersion, related_name='debugging_entry')
    status              = models.CharField(max_length=4, choices=STATUS, default=STATUS_SCHEDULED)
    error_details       = models.TextField(blank=True)
    obsolete            = models.BooleanField(default=False)

    def __unicode__(self):
        desc = u"Debugging entry of heuristic '%s', task '%s'" % (self.heuristic_version.absolutename(), self.task.fullname())

        if self.status == DebuggingEntry.STATUS_FAILED:
            return desc + u", FAILED"

        return desc

    def filename(self):
        return '%d/%d.data' % (self.heuristic_version.id, self.task.taskNumber)

    def status_text(self):
        return Experiment.STATUS_TEXTS[self.status]

    class Meta:
        verbose_name_plural = "Debugging entries"

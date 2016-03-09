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
from phpbb.models import PhpbbPost
from mash.experiments.models import Configuration, Experiment
from mash.heuristics.models import HeuristicVersion
from datetime import datetime


class Contest(models.Model):

    name                    = models.CharField(max_length=200)
    summary                 = models.CharField(max_length=512)
    description             = models.TextField(blank=True)
    configuration           = models.OneToOneField(Configuration, related_name='contest')
    reference_experiment    = models.OneToOneField(Experiment, null=True, blank=True, related_name='contest')
    start                   = models.DateTimeField()
    end                     = models.DateTimeField(null=True, blank=True)
    post                    = models.ForeignKey(PhpbbPost, null=True, blank=True)

    def __unicode__(self):
        return self.name
    
    def isFinished(self):
        now = datetime.now()
        return (self.start <= now) and (self.end is not None) and (self.end < now)

    def isInProgress(self):
        now = datetime.now()
        return (self.start <= now) and ((self.end is None) or (self.end > now))

    def isInFuture(self):
        now = datetime.now()
        return self.start > now

    def bestEntry(self):
        try:
            return self.entries.filter(rank=1, heuristic_version__heuristic__author__userprofile__project_member=False)[0]
        except:
            return None


class ContestEntry(models.Model):

    contest             = models.ForeignKey(Contest, related_name='entries')
    heuristic_version   = models.ForeignKey(HeuristicVersion, related_name='contest_entries')
    experiment          = models.OneToOneField(Experiment, related_name='contest_entry')
    rank                = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return u"Entry '%s' of '%s'" % (self.heuristic_version.fullname(), self.contest.name)

    class Meta:
        verbose_name_plural = "Contest entries"

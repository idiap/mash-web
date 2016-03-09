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


class Task(models.Model):
    
    TYPE_CLASSIFICATION     = 'c'
    TYPE_OBJECT_DETECTION   = 'od'
    TYPE_GOALPLANNING       = 'gp'

    TYPES = (
        (TYPE_CLASSIFICATION,   'Classification'),
        (TYPE_OBJECT_DETECTION, 'Object Detection'),
        (TYPE_GOALPLANNING,     'Goal-planning'),
    )
    

    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type        = models.CharField(max_length=2, choices=TYPES)
    

    def __unicode__(self):
        return self.name

    def type_name(self):
        for entry in Task.TYPES:
            if entry[0] == self.type:
                return entry[1]

        return None


class Database(models.Model):
    name              = models.CharField(max_length=200)
    url               = models.URLField(blank=True)
    doc_url           = models.URLField(blank=True)
    description       = models.TextField(blank=True)
    has_standard_sets = models.BooleanField(default=False)
    task              = models.ForeignKey(Task, related_name='databases')

    def __unicode__(self):
        return self.name


class Label(models.Model):
    database    = models.ForeignKey(Database, related_name='labels')
    index       = models.IntegerField(blank=False)
    name        = models.CharField(max_length=200, blank=False)

    def __unicode__(self):
        return self.name


class Environment(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class Goal(models.Model):
    name            = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    task            = models.ForeignKey(Task, related_name='goals')
    environments    = models.ManyToManyField(Environment, related_name='goals', null=True, blank=True)

    def __unicode__(self):
        return self.name

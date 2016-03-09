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
from django.contrib.auth.models import User
from mash.tasks.models import Task


class Classifier(models.Model):
    
    ENABLED         = 'ENA'
    DISABLED        = 'DIS'
    EXPERIMENTAL    = 'EXP'
    SYSTEM          = 'SYS'

    STATUS = (
        (ENABLED, 'Enabled'),
        (DISABLED, 'Disabled'),
        (EXPERIMENTAL, 'Experimental'),
        (SYSTEM, 'System'),
    )
    

    author      = models.ForeignKey(User, related_name='classifiers')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=3, choices=STATUS)
    known_tasks = models.ManyToManyField(Task, related_name='classifiers', null=True, blank=True)
    
    
    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        return self.author.username.lower() + '/' + self.name
 
    def enabled(self):
        return (self.status == Classifier.ENABLED)

    def disabled(self):
        return (self.status == Classifier.DISABLED)

    def experimental(self):
        return (self.status == Classifier.EXPERIMENTAL)

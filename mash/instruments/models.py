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
from django.conf import settings
from mash.experiments.models import Experiment
import os


class Instrument(models.Model):
    
    ENABLED         = 'ENA'
    DISABLED        = 'DIS'
    EXPERIMENTAL    = 'EXP'
    BUILTIN         = 'BUI'

    STATUS = (
        (ENABLED, 'Enabled'),
        (DISABLED, 'Disabled'),
        (EXPERIMENTAL, 'Experimental'),
        (BUILTIN, 'Builtin'),
    )
    

    author                      = models.ForeignKey(User, related_name='instruments')
    name                        = models.CharField(max_length=200)
    description                 = models.TextField(blank=True)
    status                      = models.CharField(max_length=3, choices=STATUS)
    task_image_classification   = models.BooleanField(default=True)
    task_object_detection       = models.BooleanField(default=True)
    task_simulator              = models.BooleanField(default=True)
    task_robotic_arm            = models.BooleanField(default=True)
    
    
    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        return self.author.username.lower() + '/' + self.name
 
    def enabled(self):
        return (self.status == Instrument.ENABLED)

    def disabled(self):
        return (self.status == Instrument.DISABLED)

    def experimental(self):
        return (self.status == Instrument.EXPERIMENTAL)

    def builtin(self):
        return (self.status == Instrument.BUILTIN)


class DataReport(models.Model):

    experiment      = models.OneToOneField(Experiment, related_name='data_report', null=True, blank=True)
    filename        = models.CharField(max_length=255)
    instruments_set = models.ManyToManyField(Instrument, null=True, blank=True)

    def __unicode__(self):
        try:
            if self.experiment is not None:
                return u"Data report of experiment '%s'" % self.experiment.fullname()
        except:
            pass
        finally:
            return u"Data report at '%s'" % self.filename

    def parentfolder(self):
        return os.path.dirname(self.filename)

    def decompressedfolder(self):
        return os.path.basename(self.filename)[:-7]

    def archivename(self):
        return os.path.basename(self.filename)


class View(models.Model):

    instrument                  = models.ForeignKey(Instrument, related_name='views')
    name                        = models.CharField(max_length=200)
    title                       = models.CharField(max_length=200)
    script                      = models.CharField(max_length=200)
    used_in_experiment_results  = models.BooleanField(default=False)
    used_in_factory_results     = models.BooleanField(default=False)
    index                       = models.PositiveIntegerField(null=True, blank=True)

    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        return self.instrument.fullname() + '/' + self.name

    def container_id(self):
        return '%s_%s_%s' % (self.instrument.author.username.lower(), self.instrument.name.lower(), self.name.lower())

    def js_start_function(self):
        return 'start_%s_%s_%s' % (self.instrument.author.username.lower(), self.instrument.name.lower(), self.name.lower())


class ViewFile(models.Model):

    CSS         = 'CSS'
    JAVASCRIPT  = 'JS'
    HTML        = 'HTML'

    FILE_TYPES = (
        (CSS, 'CSS'),
        (JAVASCRIPT, 'Javascript'),
        (HTML, 'HTML'),
    )

    view        = models.ForeignKey(View, related_name='files')
    type        = models.CharField(max_length=4, choices=FILE_TYPES)
    filename    = models.CharField(max_length=200)
    static      = models.BooleanField(default=False)
    shared      = models.BooleanField(default=False)
    require     = models.ForeignKey('self', related_name='required_by', null=True, blank=True)

    def __unicode__(self):
        return u"File '%s' of view '%s'" % (self.filename, self.view.fullname())


class Snippet(models.Model):

    UNAVAILABLE = 'UNA'
    GENERATING  = 'GEN'
    AVAILABLE   = 'AVA'
    ERROR       = 'ERR'

    STATUS = (
        (UNAVAILABLE, 'Unavailable'),
        (GENERATING, 'Generating'),
        (AVAILABLE, 'Available'),
        (ERROR, 'Error'),
    )

    report  = models.ForeignKey(DataReport, related_name='snippets')
    view    = models.ForeignKey(View, related_name='snippets')
    folder  = models.CharField(max_length=255)
    status  = models.CharField(max_length=3, choices=STATUS)


    def __unicode__(self):
        return u"Snipped generated by the view '%s' from report #%d" % (self.view.fullname(), self.report.id)

    def container_id(self):
        return self.view.container_id()

    def content(self):
        try:
            inFile = open(os.path.join(settings.SNIPPETS_ROOT, self.folder, self.view.files.filter(type=ViewFile.HTML, static=False)[0].filename), 'r')
            content = inFile.read()
            inFile.close()
            return content
        except:
            return None

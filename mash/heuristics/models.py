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


from django.core.handlers.wsgi import STATUS_CODE_TEXT
from django.db import models
from django.contrib.auth.models import User
from phpbb.models import PhpbbPost
from datetime import date
import threading
import math


class Heuristic(models.Model):
    author                  = models.ForeignKey(User, related_name='heuristics')
    name                    = models.CharField(max_length=200)
    short_description       = models.CharField(max_length=512)
    description             = models.TextField(blank=True)
    post                    = models.ForeignKey(PhpbbPost, null=True, blank=True)
    latest_public_version   = models.ForeignKey('HeuristicVersion', null=True, blank=True, related_name='latest_public_version_of')
    latest_private_version  = models.ForeignKey('HeuristicVersion', null=True, blank=True, related_name='latest_private_version_of')
    inspired_by             = models.ManyToManyField('self', related_name='derived_heuristics', symmetrical=False, null=True, blank=True)
    forum_lock              = threading.RLock()
    simple                  = models.BooleanField(default=False)


    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        return self.author.username.lower() + '/' + self.name

    def latest_version(self):
        try:
            return self.versions.exclude(status=HeuristicVersion.STATUS_DELETED).order_by('-version')[0]
        except:
            return None

    def latest_checked_version(self):
        try:
            return self.versions.filter(checked=True).order_by('-version')[0]
        except:
            return None
        
    def versions_count(self):
        return self.versions.exclude(status=HeuristicVersion.STATUS_DELETED).count()

    def public_versions_count(self):
        return self.versions.filter(public=True).count()

    def private_versions_count(self):
        return self.versions.filter(public=False).exclude(status=HeuristicVersion.STATUS_DELETED).count()

    def derived_heuristics_count(self):
        return Heuristic.objects.filter(inspired_by=self).distinct().count()
        
    def derived_heuristics(self):
        return Heuristic.objects.filter(inspired_by=self).distinct()

    def public_derived_heuristics_count(self):
        return Heuristic.objects.filter(inspired_by=self).distinct().filter(latest_public_version__isnull=False).count()

    def public_derived_heuristics(self):
        return Heuristic.objects.filter(inspired_by=self).distinct().filter(latest_public_version__isnull=False)

    def inspiration_heuristics_count(self):
        return Heuristic.objects.filter(derived_heuristics=self).distinct().count()

    def inspiration_heuristics(self):
        return Heuristic.objects.filter(derived_heuristics=self).distinct()

    def public_inspiration_heuristics_count(self):
        return Heuristic.objects.filter(derived_heuristics=self).distinct().filter(latest_public_version__isnull=False).count()

    def public_inspiration_heuristics(self):
        return Heuristic.objects.filter(derived_heuristics=self).distinct().filter(latest_public_version__isnull=False)

    def can_be_published(self):
        return self.latest_private_version and self.latest_private_version.checked and \
               (self.latest_private_version.status == HeuristicVersion.STATUS_DELETED) and \
               (not(self.latest_public_version) or (self.latest_private_version.version > self.latest_public_version.version))

    def was_deleted(self):
        return (self.versions_count() == 0)


class HeuristicVersion(models.Model):

    STATUS_OK       = 'OK'
    STATUS_DISABLED = 'DIS'
    STATUS_DELETED  = 'DEL'

    STATUS = (
        (STATUS_OK,       'OK'),
        (STATUS_DISABLED, 'Disabled'),
        (STATUS_DELETED,  'Deleted'),
    )


    heuristic           = models.ForeignKey(Heuristic, related_name='versions', null=True, blank=True)
    version             = models.PositiveIntegerField(default=1)
    filename            = models.CharField(max_length=255)
    upload_date         = models.DateTimeField('Upload date')
    publication_date    = models.DateTimeField('Publication date', null=True, blank=True)
    opensource_date     = models.DateField('Open-source date', null=True, blank=True)
    status_date         = models.DateField('Status-related date', null=True, blank=True)
    checked             = models.BooleanField(default=False)
    evaluated           = models.BooleanField(default=False)
    public              = models.BooleanField(default=False)
    status              = models.CharField(max_length=3, choices=STATUS, default=STATUS_OK)
    rank                = models.IntegerField(blank=True, null=True)


    def __unicode__(self):
        if self.heuristic is not None:
            return self.fullname()
        else:
            return "Version %d of an unknown heuristic (should be deleted soon)" % self.version

    def absolutename(self):
        return '%s/%d' % (self.heuristic.fullname(), self.version)

    def fullname(self):
        if (self.version > 1) or (self.heuristic.versions_count() > 1):
            return '%s/%d' % (self.heuristic.fullname(), self.version)
        else:
            return self.heuristic.fullname()

    def shortname(self):
        if (self.version > 1) or (self.heuristic.versions_count() > 1):
            return '%s/%d' % (self.heuristic.name, self.version)
        else:
            return self.heuristic.name

    def is_visible(self):
        return (date.today() >= self.opensource_date)

    def is_check_done(self):
        return (self.checked and (self.evaluated or self.heuristic.simple))

    def warning(self):
        if self.status != HeuristicVersion.STATUS_DISABLED:
            return ''
        
        text = 'Warning: This heuristic version has been disabled'
        
        if self.status_date is not None:
            text += ' on %s' % self.status_date.strftime('%b. %d, %Y')
        
        if self.error_reports.count() == 1:
            report = self.error_reports.all()[0]
            
            if report.is_crash():
                text += ' due to a crash'
            elif report.is_timeout():
                text += ' due to a timeout'
            elif (report.experiment is not None) and (report.experiment.isPublic() or report.experiment.isPrivate()):
                text += ' due to a problem'

            if report.experiment is not None:
                if report.experiment.isPublic():
                    text += " in experiment '%s'" % report.experiment.fullname()
                elif report.experiment.isPrivate():
                    text += " in a private experiment"
                
            text += '. See the error report below for more details.'

        elif self.error_reports.count() > 1:
            text += ' due to several problems. See the error reports below for more details.'

        else:
            text += '.'
        
        return text

    def save(self, force_insert=False, force_update=False):
        super(HeuristicVersion, self).save(force_insert, force_update)

        if self.heuristic is not None:
            if self.public:
                if (self.heuristic.latest_public_version is None) or \
                   (self.heuristic.latest_public_version.version < self.version):
                    self.heuristic.latest_public_version = self
                    self.heuristic.save(force_update=True)
            else:
                if (self.heuristic.latest_private_version is None) or  \
                   (self.heuristic.latest_private_version.version < self.version):
                    self.heuristic.latest_private_version = self
                    self.heuristic.save(force_update=True)

    def sortedEvaluationResults(self):
        return self.evaluation_results.order_by('evaluation_config__name').all()


class HeuristicTestStatus(models.Model):

    PHASE_STATUS        = 'S'
    PHASE_COMPILATION   = 'C'
    PHASE_ANALYZE       = 'A'
    PHASE_TEST          = 'T'    

    PHASES = (
        (PHASE_STATUS,      'Status'),
        (PHASE_COMPILATION, 'Compilation'),
        (PHASE_ANALYZE,     'Analyze'),
        (PHASE_TEST,        'Test'),
    )

    
    # The format is: (SUCCESS, FAILURE, INPROGRESS)
    PHASES_TEXTS = {
        PHASE_STATUS:       ('Started', 'Internal error', 'Waiting...'),
        PHASE_COMPILATION:  ('OK', 'FAILED', 'In progress...'),
        PHASE_ANALYZE:      ('OK', 'FAILED', 'In progress...'),
        PHASE_TEST:         ('OK', 'FAILED', 'In progress...'),
    }


    heuristic_version   = models.OneToOneField(HeuristicVersion, related_name='test_status')
    phase               = models.CharField(max_length=1, choices=PHASES)
    error               = models.BooleanField(default=False)
    details             = models.TextField(blank=True)

    def __unicode__(self):
        desc = u"Test status of heuristic '%s', phase '%s'" % (self.heuristic_version.absolutename(), self.phase)

        if self.error:
            return desc + u", FAILED"

        return desc

    class Meta:
        verbose_name_plural = "Heuristic test status"


class HeuristicEvaluationResults(models.Model):

    heuristic_version   = models.ForeignKey(HeuristicVersion, related_name='evaluation_results')
    evaluation_config   = models.ForeignKey('experiments.Configuration')
    experiment          = models.OneToOneField('experiments.Experiment', related_name='evaluation_results')
    rank                = models.IntegerField(blank=True, null=True)


    def __unicode__(self):
        return u"Evaluation results of heuristic '%s', configuration '%s'" % \
                    (self.heuristic_version.fullname(), self.evaluation_config.fullname())

    def mean_train_error(self):
        steps = self.steps.filter(train_error__isnull=False)
        return reduce(lambda x, y: x + y.train_error, steps, 0.0) / steps.count()

    def mean_test_error(self):
        steps = self.steps.filter(test_error__isnull=False)
        return reduce(lambda x, y: x + y.test_error, steps, 0.0) / steps.count()

    def train_error_standard_deviation(self):
        steps = self.steps.filter(train_error__isnull=False)
        return HeuristicEvaluationResults.standard_deviation(map(lambda x: x.train_error, steps))

    def test_error_standard_deviation(self):
        steps = self.steps.filter(test_error__isnull=False)
        return HeuristicEvaluationResults.standard_deviation(map(lambda x: x.test_error, steps))

    def train_text(self):
        return '%.2f%% (%.3f)' % (self.mean_train_error() * 100, self.train_error_standard_deviation() * 100)

    def test_text(self):
        return '%.2f%% (%.3f)' % (self.mean_test_error() * 100, self.test_error_standard_deviation() * 100)

    @staticmethod
    def standard_deviation(data):
        errors_sum = reduce(lambda x, y: x + y, data, 0.0)
        errors_squared_sum = reduce(lambda x, y: x + y**2, data, 0.0)
        
        mean = errors_sum / len(data)
        variance = (errors_squared_sum - errors_sum * mean) / (len(data) - 1)
        return math.sqrt(variance)

    class Meta:
        verbose_name_plural = "Heuristic evaluation results"


class HeuristicEvaluationStep(models.Model):
    evaluation_results  = models.ForeignKey(HeuristicEvaluationResults, related_name='steps') 
    seed                = models.IntegerField()
    train_error         = models.FloatField(blank=True, null=True)
    test_error          = models.FloatField(blank=True, null=True)

    def __unicode__(self):
        return u"Evaluation step of heuristic '%s', configuration '%s', seed %d" % \
                    (self.evaluation_results.heuristic_version.fullname(),
                     self.evaluation_results.evaluation_config.fullname(),
                     self.seed)


class HeuristicSignature(models.Model):

    heuristic_version   = models.ForeignKey(HeuristicVersion, related_name='signature', unique=True)
    experiment          = models.OneToOneField('experiments.Experiment', related_name='signature')

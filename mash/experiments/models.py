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
from phpbb.models import PhpbbPost
from mash.heuristics.models import HeuristicVersion
from mash.tasks.models import Task
import math
import threading


class Configuration(models.Model):

    LATEST_VERSION_ALL_HEURISTICS   = 'LVAH'
    ALL_VERSIONS_ALL_HEURISTICS     = 'AVAH'
    CUSTOM_HEURISTICS_LIST          = 'LIST'

    HEURISTICS_CHOICES = (
        (LATEST_VERSION_ALL_HEURISTICS, 'Latest versions of the public heuristics'),
        (ALL_VERSIONS_ALL_HEURISTICS,   'All versions of the public heuristics'),
        (CUSTOM_HEURISTICS_LIST,        'Custom list of heuristics'),
    )

    PUBLIC          = 'PUBL'
    PRIVATE         = 'PRIV'
    CONSORTIUM      = 'CONS'
    EVALUATION      = 'EVAL'
    CONTEST_BASE    = 'CBAS'
    CONTEST_ENTRY   = 'CENT'
    SIGNATURE       = 'SIGN'
    FACTORY         = 'FACT'

    EXPERIMENT_TYPES = (
        (PUBLIC,        'Public'),
        (PRIVATE,       'Private'),
        (CONSORTIUM,    'Consortium'),
        (EVALUATION,    'Evaluation'),
        (CONTEST_BASE,  'Contest base'),
        (CONTEST_ENTRY, 'Contest entry'),
        (SIGNATURE,     'Signature recording'),
        (FACTORY,       'Factory'),
    )


    name            = models.CharField(max_length=200)
    heuristics      = models.CharField(max_length=4, choices=HEURISTICS_CHOICES)
    heuristics_set  = models.ManyToManyField(HeuristicVersion, null=True, blank=True)
    instruments_set = models.ManyToManyField('instruments.Instrument', null=True, blank=True)
    experiment_type = models.CharField(max_length=4, choices=EXPERIMENT_TYPES)
    task            = models.ForeignKey(Task, related_name='experiments')
    
    
    def __unicode__(self):
        return self.fullname()
    
    def fullname(self):
        name = ''

        if self.experiment_type == Configuration.PUBLIC:
            name = 'public/'
        elif self.experiment_type == Configuration.PRIVATE:
            name = 'private/'
        elif self.experiment_type == Configuration.EVALUATION:
            name = 'evaluation/'
        elif (self.experiment_type == Configuration.CONTEST_BASE) or \
             (self.experiment_type == Configuration.CONTEST_ENTRY):
            name = 'contest/'
        elif self.experiment_type == Configuration.SIGNATURE:
            name = 'signature/'
        elif self.experiment_type == Configuration.FACTORY:
            name = 'factory/'
        else:
            name = 'consortium/'

        name += self.name

        return name

    def addSetting(self, name, value, section=None):
        if section is not None:
            fullname = section + '/' + name
        else:
            fullname = name

        try:
            setting = self.settings.get(name=fullname)
        except Setting.DoesNotExist:
            setting                 = Setting()
            setting.configuration   = self
            setting.name            = fullname
        
        setting.value = value
        setting.save()
    
    def databaseName(self):
        try:
            return self.settings.get(name='EXPERIMENT_SETUP/DATABASE_NAME').value
        except:
            return None

    def labels(self, index=0):
        try:
            all_labels = filter(lambda x: len(x) > 0, self.settings.get(name='EXPERIMENT_SETUP/LABELS').value.replace('\r', '').split('\n'))

            if index < len(all_labels):
                labels = all_labels[index].split(' ')
            else:
                labels = all_labels[-1].split(' ')
        except:
            return []

        cleaned_labels = []
        for label in labels:
            if label.find('-') == -1:
                cleaned_labels.append(label)
            else:
                bounds = label.split('-')
                cleaned_labels.extend([ l for l in range(int(bounds[0]), int(bounds[1]) + 1) ])

        return cleaned_labels

    def labelsCountText(self):
        labels = self.labels()
        if len(labels) > 1:
            return '%d labels' % len(labels)
        elif len(labels) == 1:
            return '1 label'
        else:
            return 'all labels'
    
    def useStandardSets(self):
        try:
            return (self.settings.get(name='EXPERIMENT_SETUP/TRAINING_SAMPLES') is None)
        except:
            return True

    def trainingRatio(self):
        try:
            return self.settings.get(name='EXPERIMENT_SETUP/TRAINING_SAMPLES').value
        except:
            return None

    def goalName(self):
        try:
            return self.settings.get(name='EXPERIMENT_SETUP/GOAL_NAME').value
        except:
            return None

    def environmentName(self):
        try:
            return self.settings.get(name='EXPERIMENT_SETUP/ENVIRONMENT_NAME').value
        except:
            return None

    def predictorName(self):
        try:
            return self.settings.get(name='USE_PREDICTOR').value
        except:
            return None

    def predictorSettings(self):
        try:
            return '\n'.join(map(lambda x: x.name[16:] + ' ' + x.value, self.settings.filter(name__startswith='PREDICTOR_SETUP/')))
        except:
            return ''

    def nbTestRounds(self):
        try:
            return int(self.settings.get(name='TEST_PREDICTOR/NB_TEST_ROUNDS').value)
        except:
            return 1

    def nbMaxActions(self):
        try:
            return int(self.settings.get(name='TEST_PREDICTOR/NB_MAX_ACTIONS').value)
        except:
            return 1000

    @staticmethod
    def getEvaluationConfigurations():
        """Returns the configurations used to evaluate a heuristic."""
        return Configuration.objects.filter(experiment_type=Configuration.EVALUATION, name__startswith='template').order_by('name')



class Setting(models.Model):
    name            = models.CharField(max_length=200)
    value           = models.TextField(blank=True)
    configuration   = models.ForeignKey(Configuration, related_name='settings')

    def __unicode__(self):
        return u"Setting '%s' of configuration '%s'" % (self.name, self.configuration.name)



class Experiment(models.Model):

    STATUS_SCHEDULED        = 'SCH'
    STATUS_RUNNING          = 'RUN'
    STATUS_DONE             = 'DONE'
    STATUS_DONE_WITH_ERRORS = 'DERR'
    STATUS_FAILED           = 'FAIL'
    STATUS_DELETED          = 'DEL'

    STATUS = (
        (STATUS_SCHEDULED,        'Scheduled'),
        (STATUS_RUNNING,          'In progress'),
        (STATUS_DONE,             'Done'),
        (STATUS_DONE_WITH_ERRORS, 'Done with errors'),
        (STATUS_FAILED,           'Failed'),
        (STATUS_DELETED,          'Deleted'),
    )

    STATUS_TEXTS = {
        STATUS_SCHEDULED:        'Scheduled',
        STATUS_RUNNING:          'In progress',
        STATUS_DONE:             'Done',
        STATUS_DONE_WITH_ERRORS: 'Done with errors',
        STATUS_FAILED:           'Failed',
        STATUS_DELETED:          'Deleted',
    }


    name            = models.CharField(max_length=200)
    configuration   = models.OneToOneField(Configuration, related_name='experiment')
    user            = models.ForeignKey(User, null=True, blank=True)
    status          = models.CharField(max_length=4, choices=STATUS, default=STATUS_SCHEDULED)
    creation_date   = models.DateTimeField(auto_now_add=True)
    start           = models.DateTimeField(null=True, blank=True)
    end             = models.DateTimeField(null=True, blank=True)
    post            = models.ForeignKey(PhpbbPost, null=True, blank=True)
    forum_lock      = threading.RLock()


    def __unicode__(self):
        return self.fullname()

    def fullname(self):
        name = ''
        
        if self.configuration.experiment_type == Configuration.PUBLIC:
            name = 'public/'
        elif self.configuration.experiment_type == Configuration.PRIVATE:
            name = 'private/'
        elif self.configuration.experiment_type == Configuration.EVALUATION:
            name = 'evaluation/'
        elif (self.configuration.experiment_type == Configuration.CONTEST_BASE) or \
             (self.configuration.experiment_type == Configuration.CONTEST_ENTRY):
            name = 'contest/'
        elif self.configuration.experiment_type == Configuration.SIGNATURE:
            name = 'signature/'
        else:
            name = 'consortium/'

        if self.user is not None:
            name += self.user.username.lower() + '/'

        name += self.name

        return name

    def duration(self):
        return self.end - self.start

    def isPublic(self):
        return (self.configuration.experiment_type == Configuration.PUBLIC)

    def isConsortium(self):
        return (self.configuration.experiment_type == Configuration.CONSORTIUM)

    def isPrivate(self):
        return (self.configuration.experiment_type == Configuration.PRIVATE)

    def isContest(self):
        return (self.configuration.experiment_type == Configuration.CONTEST_BASE) or \
               (self.configuration.experiment_type == Configuration.CONTEST_ENTRY)

    def isScheduled(self):
        return (self.status == Experiment.STATUS_SCHEDULED)

    def isRunning(self):
        return (self.status == Experiment.STATUS_RUNNING)

    def isDone(self):
        return (self.status == Experiment.STATUS_DONE) or (self.status == Experiment.STATUS_DONE_WITH_ERRORS)

    def isDoneWithErrors(self):
        return (self.status == Experiment.STATUS_DONE_WITH_ERRORS)

    def isFailed(self):
        return (self.status == Experiment.STATUS_FAILED)

    def isDeleted(self):
        return (self.status == Experiment.STATUS_DELETED)

    def status_text(self):
        return Experiment.STATUS_TEXTS[self.status]

    def stringDuration(self):
        duration = self.duration()
        result = ''
        nbSeconds = duration.seconds
        
        if duration.days > 0:
            result += '%d day' % duration.days
            if duration.days > 1:
                result += 's, '
            else: 
                result += ', '
        
        if nbSeconds >= 60 * 60:
            nb = nbSeconds / (60 * 60)
            result += '%d hour' % nb
            if nb > 1:
                result += 's, '
            else: 
                result += ', '
            nbSeconds = nbSeconds % (60 * 60)
        
        if nbSeconds >= 60:
            nb = nbSeconds / 60
            result += '%d minute' % nb
            if nb > 1:
                result += 's'
            if duration.days == 0:
                result += ', '
            nbSeconds = nbSeconds % 60
        
        if duration.days == 0:
            result += '%d second' % nbSeconds
            if nbSeconds > 1:
                result += 's'

        return result

    def gpResultsSummary(self):
        r = self.goalplanning_results.filter(training=False, result=GoalPlanningResult.RESULT_GOAL_REACHED).count()
        n = self.goalplanning_results.filter(training=False, result=GoalPlanningResult.RESULT_NONE).count()
        f = self.goalplanning_results.filter(training=False, result=GoalPlanningResult.RESULT_TASK_FAILED).count()
        return '%d / %d / %d' % (r, n, f)



class Notification(models.Model):
    name        = models.CharField(max_length=200)
    value       = models.TextField(blank=True)
    experiment  = models.ForeignKey(Experiment, related_name='notifications')

    def __unicode__(self):
        return u"Notification '%s' of experiment '%s'" % (self.name, self.experiment.fullname())



class ClassificationResults(models.Model):
    experiment      = models.OneToOneField(Experiment, related_name='classification_results')
    train_error     = models.FloatField(blank=True, null=True)
    test_error      = models.FloatField(blank=True, null=True)

    def __unicode__(self):
        return u"Results of the experiment '%s'" % self.experiment.fullname()

    def displayableTrainError(self):
        if self.train_error is not None:
            return '%.2f%%' % (self.train_error * 100.0)
    
        return '-'

    def displayableTestError(self):
        if self.test_error is not None:
            return '%.2f%%' % (self.test_error * 100.0)

        return '-'

    class Meta:
        verbose_name_plural = "Classification results"


class GoalPlanningResult(models.Model):

    experiment              = models.ForeignKey(Experiment, related_name='goalplanning_results')
    nbGoalsReached          = models.IntegerField(default=0)
    nbTasksFailed           = models.IntegerField(default=0)
    nbActionsDone           = models.IntegerField(default=0)
    nbMimickingErrors       = models.IntegerField(blank=True, null=True)
    nbNotRecommendedActions = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"Result of the experiment '%s'" % self.experiment.fullname()


class GoalPlanningRound(models.Model):

    RESULT_NONE         = 'N'
    RESULT_GOAL_REACHED = 'R'
    RESULT_TASK_FAILED  = 'F'

    RESULTS = (
        (RESULT_NONE,           'None'),
        (RESULT_GOAL_REACHED,   'Goal reached'),
        (RESULT_TASK_FAILED,    'Task failed'),
    )
   
    summary                 = models.ForeignKey(GoalPlanningResult, related_name='goalplanning_rounds')
    round                   = models.IntegerField(default=0)
    result                  = models.CharField(max_length=1, choices=RESULTS, blank=True, null=True)
    score                   = models.FloatField(blank=True, null=True)
    nbActionsDone           = models.IntegerField(default=0)
    nbMimickingErrors       = models.IntegerField(blank=True, null=True)
    nbNotRecommendedActions = models.IntegerField(blank=True, null=True)

    def result_text(self):
        for entry in GoalPlanningResult.RESULTS:
            if entry[0] == self.result:
                return entry[1]

        return None

    def __unicode__(self):
        return u"Result of the test round #%d" % (self.round)


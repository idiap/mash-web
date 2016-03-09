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


import unittest
from base_task_test import BaseTaskTest
from implemented_tasks.heuristic_ranker import HeuristicRanker
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicEvaluationResults
from mash.heuristics.models import HeuristicEvaluationStep
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
from mash.experiments.models import ClassificationResults
from mash.contests.models import Contest
from mash.contests.models import ContestEntry
from mash.tasks.models import Task as DBTask
from mash.servers.models import Job
from mash.accounts.models import UserProfile
from django.contrib.auth.models import User
from pymash.messages import Message
from datetime import datetime
import time
import os
import shutil


class EvaluatedHeuristicRankerTestCase(BaseTaskTest):

    def setUp(self):
        self.task = None
        self.tearDown()

    def tearDown(self):
        HeuristicEvaluationStep.objects.all().delete()
        HeuristicEvaluationResults.objects.all().delete()
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        Configuration.objects.all().delete()
        Experiment.objects.all().delete()
        User.objects.all().delete()
        Job.objects.all().delete()
        DBTask.objects.all().delete()

        if self.task is not None:
            del self.task

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def util_create_configuration(self, name):
        try:
            task = DBTask.objects.all()[0]
        except:
            task = DBTask()
            task.name = 'name1'
            task.type = DBTask.TYPE_CLASSIFICATION
            task.save()

        if not(name.startswith('template/')):
            name = 'template/' + name

        configuration = Configuration()
        configuration.name = name
        configuration.heuristics = Configuration.CUSTOM_HEURISTICS_LIST
        configuration.experiment_type = Configuration.EVALUATION
        configuration.task = task
        configuration.save()


    def util_create_heuristic(self, username, heuristic_name, public, test_errors, version_number=1):
        try:
            user = User.objects.get(username=username)
        except:
            user = User()
            user.username = username
            user.save()
        
        try:
            heuristic = Heuristic.objects.get(name=heuristic_name)
        except:
            heuristic = Heuristic()
            heuristic.author = user
            heuristic.name = heuristic_name
            heuristic.save()

        version = HeuristicVersion()
        version.heuristic = heuristic
        version.version = version_number
        version.filename = '%s.cpp' % heuristic_name
        version.upload_date = datetime.now()
        version.status_date = datetime.now()
        version.checked = True
        version.public = public
        version.save()
        
        if public:
            if (heuristic.latest_public_version is None) or (heuristic.latest_public_version.version < version_number):
                heuristic.latest_public_version = version
        else:
            if (heuristic.latest_private_version is None) or (heuristic.latest_private_version.version < version_number):
                heuristic.latest_private_version = version
        heuristic.save()
        
        for index, evaluation_configuration in enumerate(Configuration.objects.filter(name__startswith='template/').order_by('id')):
            configuration = Configuration()
            configuration.name = evaluation_configuration.name.replace('template/', '%s/' % heuristic_name)
            configuration.heuristics = evaluation_configuration.heuristics
            configuration.experiment_type = evaluation_configuration.experiment_type
            configuration.task = evaluation_configuration.task
            configuration.save()

            experiment = Experiment()
            experiment.name = configuration.name
            experiment.configuration = configuration
            experiment.creation_date = datetime.now()

            if len(filter(lambda x: x is None, test_errors[index])) == 0:
                experiment.status = Experiment.STATUS_DONE
            else:
                experiment.status = Experiment.STATUS_RUNNING

            experiment.save()
                    
            evaluation_results = HeuristicEvaluationResults()
            evaluation_results.heuristic_version = version
            evaluation_results.evaluation_config = evaluation_configuration
            evaluation_results.experiment = experiment
            evaluation_results.rank = None
            evaluation_results.save()

            for index2, test_error in enumerate(test_errors[index]):
                step = HeuristicEvaluationStep()
                step.evaluation_results = evaluation_results
                step.seed = 1000 + index2
                step.train_error = 0.5
                step.test_error = test_error
                step.save()
        
        version.evaluated = (version.evaluation_results.filter(experiment__status=Experiment.STATUS_RUNNING).count() == 0)
        version.save()


    def test_rank_evaluated_heuristics__no_heuristics(self):

        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())


    def test_rank_evaluated_heuristics(self):
        
        self.util_create_configuration('config1')
        self.util_create_configuration('config2')
        
        self.util_create_heuristic('user1', 'heuristic1', True, test_errors=[[0.1, 0.2, 0.05], [0.1, 0.2, 0.15]])
        self.util_create_heuristic('user1', 'heuristic2', True, test_errors=[[0.01, 0.02, 0.005], [0.01, 0.02, 0.015]])
        self.util_create_heuristic('user2', 'heuristic2', True, test_errors=[[0.2, 0.25, 0.15], [0.3, 0.4, 0.5]], version_number=2)
        self.util_create_heuristic('user2', 'heuristic3', False, test_errors=[[0.3, 0.25, 0.35], [0.2, 0.3, 0.25]])
        self.util_create_heuristic('user3', 'heuristic4', False, test_errors=[[0.4, 0.35, 0.45], [0.3, None, None]])
        self.util_create_heuristic('user4', 'heuristic5', True, test_errors=[[0.05, 0.03, 0.07], [0.3, None, None]])
        
        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   heuristic_version__version=1,
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   heuristic_version__version=2,
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic4',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic5',
                                                                   evaluation_config__name='template/config1').rank)

        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   heuristic_version__version=1,
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   heuristic_version__version=2,
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertTrue(HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic4',
                                                               evaluation_config__name='template/config2').rank is None)
        self.assertTrue(HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic5',
                                                               evaluation_config__name='template/config2').rank is None)

        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic1').rank)
        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic2', version=1).rank)
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic2', version=2).rank)
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic3').rank)
        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic4').rank is None)
        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic5').rank is None)


    def test_event_private_heuristic_evaluated__one_configuration(self):

        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.util_create_heuristic('user1', 'heuristic1', True, test_errors=[[0.1, 0.2, 0.05], [0.1, 0.2, 0.15]])
        self.util_create_heuristic('user2', 'heuristic2', True, test_errors=[[0.2, 0.25, 0.15], [0.3, 0.4, 0.5]])

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.util_create_heuristic('user3', 'heuristic3', False, test_errors=[[0.3, 0.25, 0.35], [0.2, None, None]])

        self.assertFalse(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)

        self.assertTrue(self.task.processMessage(Message('EVT_HEURISTIC_EVALUATED', [HeuristicVersion.objects.get(heuristic__name='heuristic3').id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config1').rank)

        self.assertTrue(HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                               evaluation_config__name='template/config2').rank is None)

        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic3').rank is None)
        self.assertFalse(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)


    def test_event_private_heuristic_evaluated__all_configurations(self):

        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.util_create_heuristic('user1', 'heuristic1', True, test_errors=[[0.1, 0.2, 0.05], [0.1, 0.2, 0.15]])
        self.util_create_heuristic('user2', 'heuristic2', True, test_errors=[[0.2, 0.25, 0.15], [0.3, 0.4, 0.5]])

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.util_create_heuristic('user3', 'heuristic3', False, test_errors=[[0.3, 0.25, 0.35], [0.2, 0.3, 0.25]])

        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)

        self.assertTrue(self.task.processMessage(Message('EVT_HEURISTIC_EVALUATED', [HeuristicVersion.objects.get(heuristic__name='heuristic3').id])))

        self.util_wait_jobs_completion([self.task])
        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config1').rank)

        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config2').rank)

        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic3').rank)


    def test_event_public_heuristic_evaluated__one_configuration(self):

        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.util_create_heuristic('user1', 'heuristic1', True, test_errors=[[0.1, 0.2, 0.05], [0.1, 0.2, 0.15]])
        self.util_create_heuristic('user2', 'heuristic2', True, test_errors=[[0.2, 0.25, 0.15], [0.3, 0.4, 0.5]])

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.util_create_heuristic('user3', 'heuristic3', True, test_errors=[[0.3, 0.25, 0.35], [0.2, None, None]])

        self.assertFalse(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)

        self.assertTrue(self.task.processMessage(Message('EVT_HEURISTIC_EVALUATED', [HeuristicVersion.objects.get(heuristic__name='heuristic3').id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())


        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config1').rank)

        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertTrue(HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                               evaluation_config__name='template/config2').rank is None)

        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic1').rank)
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic2').rank)
        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic3').rank is None)
        self.assertFalse(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)


    def test_event_public_heuristic_evaluated__all_configurations(self):

        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.util_create_heuristic('user1', 'heuristic1', True, test_errors=[[0.1, 0.2, 0.05], [0.1, 0.2, 0.15]])
        self.util_create_heuristic('user2', 'heuristic2', True, test_errors=[[0.2, 0.25, 0.15], [0.3, 0.4, 0.5]])

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage('RANK_EVALUATED_HEURISTICS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.util_create_heuristic('user3', 'heuristic3', True, test_errors=[[0.3, 0.25, 0.35], [0.2, 0.3, 0.25]])

        self.assertTrue(HeuristicVersion.objects.get(heuristic__name='heuristic3').evaluated)

        self.assertTrue(self.task.processMessage(Message('EVT_HEURISTIC_EVALUATED', [HeuristicVersion.objects.get(heuristic__name='heuristic3').id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   evaluation_config__name='template/config1').rank)
        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config1').rank)

        self.assertEqual(1, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic1',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(3, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic2',
                                                                   evaluation_config__name='template/config2').rank)
        self.assertEqual(2, HeuristicEvaluationResults.objects.get(heuristic_version__heuristic__name='heuristic3',
                                                                   evaluation_config__name='template/config2').rank)

        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic1').rank)
        self.assertEqual(3, HeuristicVersion.objects.get(heuristic__name='heuristic2').rank)
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic3').rank)



class ContestEntriesRankerTestCase(BaseTaskTest):

    def setUp(self):
        self.task = None
        self.tearDown()

    def tearDown(self):
        ContestEntry.objects.all().delete()
        Contest.objects.all().delete()
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        Configuration.objects.all().delete()
        ClassificationResults.objects.all().delete()
        Experiment.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.all().delete()
        Job.objects.all().delete()
        DBTask.objects.all().delete()

        if self.task is not None:
            del self.task

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def util_create_contest(self):
        try:
            task = DBTask.objects.all()[0]
        except:
            task = DBTask()
            task.name = 'name1'
            task.type = DBTask.TYPE_CLASSIFICATION
            task.save()

        configuration = Configuration()
        configuration.name = 'config1'
        configuration.heuristics = Configuration.CUSTOM_HEURISTICS_LIST
        configuration.experiment_type = Configuration.CONTEST_ENTRY
        configuration.task = task
        configuration.save()

        contest = Contest()
        contest.name = 'contest1'
        contest.configuration = configuration
        contest.start = datetime.now()
        contest.save()
        
        return contest


    def util_create_contest_entry(self, username, heuristic_name, test_error, train_error):
        try:
            user = User.objects.get(username=username)
        except:
            user = User()
            user.username = username
            user.save()
            
            profile = UserProfile()
            profile.project_member = False
            profile.user = user
            profile.save()

        heuristic = Heuristic()
        heuristic.author = user
        heuristic.name = heuristic_name
        heuristic.save()

        version = HeuristicVersion()
        version.heuristic = heuristic
        version.version = 1
        version.filename = '%s.cpp' % heuristic_name
        version.upload_date = datetime.now()
        version.status_date = datetime.now()
        version.checked = True
        version.evaluated = True
        version.public = True
        version.save()

        heuristic.latest_public_version = version
        heuristic.save()

        reference_configuration = Configuration.objects.get(name='config1')

        configuration = Configuration()
        configuration.name = reference_configuration.name + '/' + heuristic_name
        configuration.heuristics = reference_configuration.heuristics
        configuration.experiment_type = reference_configuration.experiment_type
        configuration.task = reference_configuration.task
        configuration.save()

        experiment = Experiment()
        experiment.name = heuristic_name
        experiment.configuration = configuration
        experiment.creation_date = datetime.now()

        if test_error is not None:
            experiment.status = Experiment.STATUS_DONE
        else:
            experiment.status = Experiment.STATUS_RUNNING

        experiment.save()

        classification_results = ClassificationResults()
        classification_results.experiment = experiment
        classification_results.train_error = train_error
        classification_results.test_error = test_error
        classification_results.save()

        contest_entry = ContestEntry()
        contest_entry.contest = Contest.objects.get(name='contest1')
        contest_entry.heuristic_version = version
        contest_entry.experiment = experiment
        contest_entry.rank = None
        contest_entry.save()


    def test_rank_contest_entries__no_entries(self):

        contest = self.util_create_contest()

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage(Message('RANK_CONTEST_ENTRIES', [contest.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(0, ContestEntry.objects.filter(rank__isnull=False).count())


    def test_rank_contest_entries__no_done_entries(self):

        contest = self.util_create_contest()
        
        self.util_create_contest_entry('user1', 'heuristic1', None, None)
        self.util_create_contest_entry('user1', 'heuristic2', None, 0.5)

        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage(Message('RANK_CONTEST_ENTRIES', [contest.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(0, ContestEntry.objects.filter(rank__isnull=False).count())


    def test_rank_contest_entries(self):
    
        contest = self.util_create_contest()
    
        self.util_create_contest_entry('user1', 'heuristic1', 0.5, 0.6)
        self.util_create_contest_entry('user1', 'heuristic2', 0.8, 0.5)
        self.util_create_contest_entry('user2', 'heuristic3', 0.3, 0.4)
        self.util_create_contest_entry('user3', 'heuristic4', 0.3, 0.2)
        self.util_create_contest_entry('user4', 'heuristic5', 0.2, 0.2)
        self.util_create_contest_entry('user4', 'heuristic6', None, 0.2)
    
        self.task = HeuristicRanker()
        self.task.start()

        self.assertTrue(self.task.processMessage(Message('RANK_CONTEST_ENTRIES', [contest.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(5, ContestEntry.objects.filter(rank__isnull=False).count())
        self.assertEqual(1, ContestEntry.objects.filter(rank__isnull=True).count())
    
        self.assertEqual(4, ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic1').rank)
        self.assertEqual(5, ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic2').rank)
        self.assertEqual(3, ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic3').rank)
        self.assertEqual(2, ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic4').rank)
        self.assertEqual(1, ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic5').rank)
        self.assertTrue(ContestEntry.objects.get(heuristic_version__heuristic__name='heuristic6').rank is None)



def tests():
    return [ EvaluatedHeuristicRankerTestCase,
             ContestEntriesRankerTestCase,
           ]

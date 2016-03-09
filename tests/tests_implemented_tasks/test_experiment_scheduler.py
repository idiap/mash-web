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
from implemented_tasks.experiment_scheduler import ExperimentScheduler
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicEvaluationResults
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
from mash.tasks.models import Task as DBTask
from mash.servers.models import Job
from django.contrib.auth.models import User
from pymash.messages import Message
from datetime import datetime
import time
import os
import shutil


class ExperimentSchedulerHeuristicEvaluationTestCase(BaseTaskTest):

    def setUp(self):
        self.task = None
        self.tearDown()

    def tearDown(self):
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


    def util_create_configuration(self, name, template=True, evaluation=True):
        try:
            task = DBTask.objects.all()[0]
        except:
            task = DBTask()
            task.name = 'name1'
            task.type = DBTask.TYPE_CLASSIFICATION
            task.save()

        if template and not(name.startswith('template/')):
            name = 'template/' + name

        configuration = Configuration()
        configuration.name = name
        configuration.heuristics = Configuration.CUSTOM_HEURISTICS_LIST
        if evaluation :
            configuration.experiment_type = Configuration.EVALUATION
        else :
            configuration.experiment_type = Configuration.SIGNATURE
        configuration.task = task
        configuration.save()
        
        return configuration


    def util_create_heuristic(self, username, heuristic_name, public):
        try:
            user = User.objects.get(username=username)
        except:
            user = User()
            user.username = username
            user.save()
        
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
        version.public = public
        version.save()
        
        if public:
            heuristic.latest_public_version = version
        else:
            heuristic.latest_private_version = version
        heuristic.save()
        
        return heuristic


    def util_setup(self):
        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.task = ExperimentScheduler()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())


    def test_startup_no_heuristic(self):
        self.task = ExperimentScheduler()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())


    def test_startup_one_heuristic_to_check(self):
        self.util_create_configuration('config1')
        self.util_create_configuration('config2')
        self.util_create_configuration('signature1', template=True, evaluation=False)

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)

        self.task = ExperimentScheduler()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(3, Job.objects.count())
        self.assertEqual(3, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(3, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)


    def test_evaluation_scheduling(self):
        self.util_setup()
        
        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic.versions.all()[0].id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)


    def test_evaluation_of_all_heuristics_scheduling(self):
        self.util_setup()

        self.util_create_heuristic('user1', 'heuristic1', False)
        self.util_create_heuristic('user2', 'heuristic2', True)

        self.assertTrue(self.task.processMessage(Message('EVALUATE_ALL_HEURISTICS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(3, Job.objects.count())
        self.assertEqual(3, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(4, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic2').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic2',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic2',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()
        m3 = self.task.out_channel.waitMessage()
        m4 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertEqual('RUN_EXPERIMENT', m3.name)
        self.assertEqual('RUN_EXPERIMENT', m4.name)

        self.assertNotEqual(m1.parameters[0], m2.parameters[0])
        self.assertNotEqual(m1.parameters[0], m3.parameters[0])
        self.assertNotEqual(m1.parameters[0], m4.parameters[0])
        self.assertNotEqual(m2.parameters[0], m3.parameters[0])
        self.assertNotEqual(m2.parameters[0], m4.parameters[0])
        self.assertNotEqual(m3.parameters[0], m4.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m3.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m4.parameters[0]) is not None)


    def test_evaluation_scheduling_of_already_evaluated_heuristic(self):
        self.util_setup()

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)
        heuristic_version = heuristic.versions.all()[0]

        experiment = Experiment()
        experiment.name = 'experiment1'
        experiment.configuration = self.util_create_configuration('experiment1', template=False)
        experiment.status = Experiment.STATUS_DONE
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config1')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        experiment = Experiment()
        experiment.name = 'experiment2'
        experiment.configuration = self.util_create_configuration('experiment2', template=False)
        experiment.status = Experiment.STATUS_DONE
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config2')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        heuristic_version.evaluated = True
        heuristic_version.save()

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic_version.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.filter(evaluation_results__isnull=False).count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)


    def test_evaluation_scheduling_of_currently_evaluated_heuristic(self):
        self.util_setup()

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)
        heuristic_version = heuristic.versions.all()[0]

        experiment = Experiment()
        experiment.name = 'experiment1'
        experiment.configuration = self.util_create_configuration('experiment1', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config1')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        experiment = Experiment()
        experiment.name = 'experiment2'
        experiment.configuration = self.util_create_configuration('experiment2', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config2')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic_version.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('CANCEL_EXPERIMENT', m1.name)
        self.assertEqual('CANCEL_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)


    def test_evaluation_scheduling_of_partially_evaluated_heuristic(self):
        self.util_setup()

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)
        heuristic_version = heuristic.versions.all()[0]

        experiment = Experiment()
        experiment.name = 'experiment1'
        experiment.configuration = self.util_create_configuration('experiment1', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config1')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        experiment = Experiment()
        experiment.name = 'experiment2'
        experiment.configuration = self.util_create_configuration('experiment2', template=False)
        experiment.status = Experiment.STATUS_DONE
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config2')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_HEURISTIC_EVALUATION', [heuristic_version.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(0, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m = self.task.out_channel.waitMessage()
        self.assertEqual('CANCEL_EXPERIMENT', m.name)
        self.assertTrue(Experiment.objects.get(id=m.parameters[0]) is not None)


    def test_event_heuristic_checked(self):
        self.util_setup()
        self.util_create_configuration('signature1', template=True, evaluation=False)

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)

        self.assertTrue(self.task.processMessage(Message('EVT_HEURISTIC_CHECKED', [heuristic.versions.all()[0].id])))

        self.util_wait_jobs_completion([self.task])

        
        self.assertEqual(3, Job.objects.count())
        self.assertEqual(3, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(3, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)

    def test_event_one_evaluation_experiment_cancelled(self):
        self.util_setup()

        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)
        heuristic_version = heuristic.versions.all()[0]

        experiment = Experiment()
        experiment.name = 'experiment1'
        experiment.configuration = self.util_create_configuration('experiment1', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config1')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        experiment = Experiment()
        experiment.name = 'experiment2'
        experiment.configuration = self.util_create_configuration('experiment2', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()

        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config2')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()

        self.assertTrue(self.task.processMessage(Message('EVT_EXPERIMENT_CANCELLED', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        # No job really done
        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(0, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())


    def test_event_last_evaluation_experiment_cancelled(self):
        self.util_setup()
      
        heuristic = self.util_create_heuristic('user1', 'heuristic1', False)
        heuristic_version = heuristic.versions.all()[0]
      
        experiment = Experiment()
        experiment.name = 'experiment1'
        experiment.configuration = self.util_create_configuration('experiment1', template=False)
        experiment.status = Experiment.STATUS_RUNNING
        experiment.save()
      
        evaluation_results = HeuristicEvaluationResults()
        evaluation_results.experiment = experiment
        evaluation_results.evaluation_config = Configuration.objects.get(name='template/config1')
        evaluation_results.heuristic_version = heuristic_version
        evaluation_results.save()
      
        self.assertTrue(self.task.processMessage(Message('EVT_EXPERIMENT_CANCELLED', [experiment.id])))
      
        self.util_wait_jobs_completion([self.task])
      
        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, HeuristicVersion.objects.get(heuristic__name='heuristic1').evaluation_results.count())

        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config1').count())
        self.assertEqual(1, HeuristicEvaluationResults.objects.filter(heuristic_version__heuristic__name='heuristic1',
                                                                      evaluation_config__name='template/config2').count())

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)



class ExperimentSchedulerPublicExperimentTestCase(BaseTaskTest):

    def setUp(self):
        self.task = None
        self.tearDown()

    def tearDown(self):
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        Configuration.objects.all().delete()
        Experiment.objects.all().delete()
        User.objects.all().delete()
        Job.objects.all().delete()

        if self.task is not None:
            del self.task

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def util_create_configuration(self, name, template=True):
        try:
            task = DBTask.objects.all()[0]
        except:
            task = DBTask()
            task.name = 'name1'
            task.type = DBTask.TYPE_CLASSIFICATION
            task.save()

        if template and not(name.startswith('template/')):
            name = 'template/' + name

        configuration = Configuration()
        configuration.name = name
        configuration.heuristics = Configuration.LATEST_VERSION_ALL_HEURISTICS
        configuration.experiment_type = Configuration.PUBLIC
        configuration.task = task
        configuration.save()

        return configuration


    def util_create_heuristic(self, username, heuristic_name):
        try:
            user = User.objects.get(username=username)
        except:
            user = User()
            user.username = username
            user.save()

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

        return heuristic

    
    def util_create_public_experiment(self, template, heuristics, status=Experiment.STATUS_DONE):
        # Create the configuration
        configuration                 = Configuration()
        configuration.name            = template.name.replace('template/', '') + '/' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        configuration.heuristics      = template.heuristics
        configuration.experiment_type = template.experiment_type
        configuration.task            = template.task
        configuration.save()

        # Add the list of heuristic versions
        for heuristic in heuristics:
            configuration.heuristics_set.add(heuristic.latest_public_version)

        # Save the configuration 
        configuration.save()

        # Create the experiment
        experiment               = Experiment()
        experiment.name          = configuration.name
        experiment.configuration = configuration
        experiment.status        = status
        experiment.save()
        
        return experiment


    def util_setup(self, nb_configurations=2):
        for i in range(1, nb_configurations + 1):
            self.util_create_configuration('config%d' % i)

        self.task = ExperimentScheduler()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        try:
            print Job.objects.all()[0].alert.details
        except:
            pass

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())


    def test_startup_no_heuristic(self):
        self.util_create_configuration('config1')
        self.util_create_configuration('config2')

        self.task = ExperimentScheduler()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(0, Experiment.objects.count())


    def test_public_experiments_scheduling(self):
        self.util_setup()

        heuristic = self.util_create_heuristic('user1', 'heuristic1')

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())

        for experiment in Experiment.objects.all():
            self.assertTrue(experiment.configuration.heuristics_set.get(heuristic__name='heuristic1') is not None)

        m1 = self.task.out_channel.waitMessage()
        m2 = self.task.out_channel.waitMessage()

        self.assertEqual('RUN_EXPERIMENT', m1.name)
        self.assertEqual('RUN_EXPERIMENT', m2.name)
        self.assertNotEqual(m1.parameters[0], m2.parameters[0])

        self.assertTrue(Experiment.objects.get(id=m1.parameters[0]) is not None)
        self.assertTrue(Experiment.objects.get(id=m2.parameters[0]) is not None)


    def test_public_experiments_scheduling_no_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1])

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_public_experiments_scheduling_one_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')
        heuristic2 = self.util_create_heuristic('user1', 'heuristic2')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1])

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())

        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic1') is not None)
        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic2') is not None)

        m = self.task.out_channel.waitMessage()
        self.assertEqual('RUN_EXPERIMENT', m.name)
        self.assertNotEqual(experiment.id, m.parameters[0])
        self.assertTrue(Experiment.objects.get(id=m.parameters[0]) is not None)


    def test_public_experiments_scheduling_while_already_running_no_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_RUNNING)

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_public_experiments_scheduling_while_already_running_one_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')
        heuristic2 = self.util_create_heuristic('user1', 'heuristic2')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_RUNNING)

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_public_experiments_scheduling_while_scheduled_no_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_SCHEDULED)

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_public_experiments_scheduling_while_scheduled_one_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')
        heuristic2 = self.util_create_heuristic('user1', 'heuristic2')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_SCHEDULED)

        self.assertTrue(self.task.processMessage(Message('SCHEDULE_PUBLIC_EXPERIMENTS')))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())

        m = self.task.out_channel.waitMessage()
        self.assertEqual('CANCEL_EXPERIMENT', m.name)
        self.assertEqual(experiment.id, m.parameters[0])


    def test_event_experiment_cancelled(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1])

        self.assertTrue(self.task.processMessage(Message('EVT_EXPERIMENT_CANCELLED', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())

        self.assertTrue(Experiment.objects.all()[0].configuration.heuristics_set.get(heuristic__name='heuristic1') is not None)

        m = self.task.out_channel.waitMessage()
        self.assertEqual('RUN_EXPERIMENT', m.name)
        self.assertTrue(Experiment.objects.get(id=m.parameters[0]) is not None)


    def test_event_public_experiment_done_no_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_DONE)

        self.assertTrue(self.task.processMessage(Message('EVT_PUBLIC_EXPERIMENT_DONE', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_event_public_experiment_done_one_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')
        heuristic2 = self.util_create_heuristic('user1', 'heuristic2')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_DONE)

        self.assertTrue(self.task.processMessage(Message('EVT_PUBLIC_EXPERIMENT_DONE', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())

        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic1') is not None)
        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic2') is not None)

        m = self.task.out_channel.waitMessage()
        self.assertEqual('RUN_EXPERIMENT', m.name)
        self.assertNotEqual(experiment.id, m.parameters[0])
        self.assertTrue(Experiment.objects.get(id=m.parameters[0]) is not None)


    def test_event_public_experiment_failed_no_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_FAILED)

        self.assertTrue(self.task.processMessage(Message('EVT_PUBLIC_EXPERIMENT_FAILED', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(1, Experiment.objects.count())
        self.assertEqual(1, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())
        self.assertEqual(1, Experiment.objects.filter(id=experiment.id).count())


    def test_event_public_experiment_failed_one_new_heuristic(self):
        self.util_setup(nb_configurations=1)

        heuristic1 = self.util_create_heuristic('user1', 'heuristic1')
        heuristic2 = self.util_create_heuristic('user1', 'heuristic2')

        experiment = self.util_create_public_experiment(Configuration.objects.get(name='template/config1'), [heuristic1], status=Experiment.STATUS_FAILED)

        self.assertTrue(self.task.processMessage(Message('EVT_PUBLIC_EXPERIMENT_FAILED', [experiment.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(2, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(2, Experiment.objects.count())
        self.assertEqual(2, Experiment.objects.filter(configuration__experiment_type=Configuration.PUBLIC).count())

        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic1') is not None)
        self.assertTrue(Experiment.objects.exclude(id=experiment.id).all()[0].configuration.heuristics_set.get(heuristic__name='heuristic2') is not None)

        m = self.task.out_channel.waitMessage()
        self.assertEqual('RUN_EXPERIMENT', m.name)
        self.assertNotEqual(experiment.id, m.parameters[0])
        self.assertTrue(Experiment.objects.get(id=m.parameters[0]) is not None)



def tests():
    return [ ExperimentSchedulerHeuristicEvaluationTestCase,
             ExperimentSchedulerPublicExperimentTestCase,
           ]

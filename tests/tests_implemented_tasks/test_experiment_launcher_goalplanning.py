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
from base_experiment_launcher_test import BaseExperimentLauncherTest
from mash.servers.models import Server
from mash.servers.models import Job
from mash.servers.models import Alert
from mash.heuristics.models import HeuristicVersion
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
from mash.experiments.models import GoalPlanningResult
from mash.experiments.models import Notification
from mash.instruments.models import Instrument
from mash.goalplanners.models import Goalplanner
from mash.tasks.models import Task as DBTask
from mash.tasks.models import Goal
from mash.tasks.models import Environment
from mash.tools.models import PluginErrorReport
from mash.contests.models import Contest
from mash.contests.models import ContestEntry
from mash.accounts.models import UserProfile
from mocks.mock_server_listeners import MockExperimentServerListener
from pymash.messages import Message
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime
import os


class ExperimentLauncherGoalPlanningBaseTestCase(BaseExperimentLauncherTest):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningBaseTestCase, self).setUp()

        task      = DBTask()
        task.name = 'Robot'
        task.type = DBTask.TYPE_GOALPLANNING
        task.save()

        environment      = Environment()
        environment.name = 'test_environment'
        environment.save()

        goal      = Goal()
        goal.name = 'test_goal'
        goal.task = task
        goal.save()
        
        goal.environments.add(environment)

        self.experiment_type = Configuration.PRIVATE
        self.seeds = None


    def util_createExperiment(self, experiment_type=Configuration.PUBLIC, goal_name='test_goal',
                              environment_name='test_environment', task=None, seeds=None):

        try:
            user = User.objects.get(username='user1')
        except:
            user = User()
            user.username = 'user1'
            user.save()
        
        try:
            profile = UserProfile.objects.get(user=user)
        except:
            profile = UserProfile()
            profile.user = user
            profile.save()
        
        goalplanner = Goalplanner()
        goalplanner.author = user
        goalplanner.name = 'predictor1'
        goalplanner.status = Goalplanner.ENABLED
        goalplanner.save()

        configuration = Configuration()

        if self.experiment_type == Configuration.CONTEST_BASE:
            configuration.name = 'config1/base'
        else:
            configuration.name = 'config1'

        configuration.heuristics      = Configuration.CUSTOM_HEURISTICS_LIST
        configuration.experiment_type = experiment_type

        if task is None:
            configuration.task = DBTask.objects.all()[0]
        else:
            configuration.task = task

        configuration.save()

        configuration.heuristics_set.add(self.util_create_heuristic(user_name='user1', heuristic_name='heuristic1'))
        configuration.heuristics_set.add(self.util_create_heuristic(user_name='user2', heuristic_name='heuristic2'))
        configuration.heuristics_set.add(self.util_create_heuristic(user_name='user3', heuristic_name='heuristic3'))

        configuration.instruments_set.add(self.util_create_instrument(user_name='user1', instrument_name='instrument1'))
        configuration.instruments_set.add(self.util_create_instrument(user_name='user2', instrument_name='instrument2'))

        configuration.addSetting('EXPERIMENT_SETUP/GOAL_NAME', goal_name)
        configuration.addSetting('EXPERIMENT_SETUP/ENVIRONMENT_NAME', environment_name)
        configuration.addSetting('INSTRUMENT_SETUP/user1/instrument1/INSTRUMENT_TEST', 'OFF')
        configuration.addSetting('PREDICTOR_SETUP/PREDICTOR_TEST', 'ON')
        configuration.addSetting('USE_PREDICTOR', 'user1/predictor1')
        
        if seeds is not None:
            configuration.addSetting('USE_GLOBAL_SEED', seeds)

        self.experiment               = Experiment()
        self.experiment.name          = 'experiment1'
        self.experiment.configuration = configuration
        self.experiment.save()

        if self.experiment_type == Configuration.CONTEST_ENTRY:
            contest                         = Contest()
            contest.name                    = 'contest1'
            contest.configuration           = configuration
            contest.reference_experiment    = None
            contest.start                   = datetime.now()
            contest.save()

            contest_entry                   = ContestEntry()
            contest_entry.contest           = contest
            contest_entry.heuristic_version = HeuristicVersion.objects.get(heuristic__name='heuristic1')
            contest_entry.experiment        = self.experiment
            contest_entry.rank              = None
            contest_entry.save()


    def util_createApplicationServer(self):
        server                      = Server()
        server.name                 = 'Mazox'
        server.address              = '127.0.0.1'
        server.port                 = 19000
        server.server_type          = Server.APPLICATION_SERVER
        server.subtype              = Server.SUBTYPE_INTERACTIVE
        server.status               = Server.SERVER_STATUS_ONLINE
        server.save()

        server.supported_tasks.add(DBTask.objects.all()[0])
        server.provided_goals.add(Goal.objects.all()[0])



class ExperimentLauncherGoalPlanningServersTestCase(ExperimentLauncherGoalPlanningBaseTestCase):

    def test_no_application_server_in_database(self):
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment()

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())


    def test_no_application_server_providing_the_goal(self):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment(goal_name='unknown')

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())


    def test_no_application_server_online(self):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start(no_application_server=True)
        self.util_createExperiment()

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())


    def test_no_experiment_server_in_database(self):
        self.util_createApplicationServer()
        self.util_start()
        self.util_createExperiment()

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())


    def test_no_experiment_server_supporting_the_task(self):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()

        task      = DBTask()
        task.name = 'GoalPlanning2'
        task.type = DBTask.TYPE_GOALPLANNING
        task.save()

        self.util_createExperiment(task=task)

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())


    def test_no_experiment_server_online(self):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start(no_experiment_server=True)
        self.util_createExperiment()

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())



class ExperimentLauncherGoalPlanningFailureTestCase(ExperimentLauncherGoalPlanningBaseTestCase):

    def util_createPredictorModel(self, model=None, internal_data=None):
        if model is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_MODEL', 'test.model')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.model'), 'w')
            outFile.write(model)
            outFile.close()

        if internal_data is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_INTERNAL_DATA', 'test.internal')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.internal'), 'w')
            outFile.write(internal_data)
            outFile.close()
        

    def util_test_error_base(self, fail_condition, model=None, internal_data=None):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment(self.experiment_type)
        self.util_createPredictorModel(model, internal_data)

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())
        self.assertEqual(0, Notification.objects.count())

        MockExperimentServerListener.FAIL_CONDITION = fail_condition

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_FAILED).count())

        self.assertEqual(1, Alert.objects.count())

        experiment = Experiment.objects.get(id=self.experiment.id)
        self.assertEqual(Experiment.STATUS_FAILED, experiment.status)
        
        self.assertEqual(fail_condition, MockExperimentServerListener.LAST_COMMAND.name)

        self.util_post_test()


    def util_post_test(self):
        pass


    def test_error_with_experiment_type(self):
        self.util_test_error_base('SET_EXPERIMENT_TYPE')


    def test_error_with_application_server(self):
        self.util_test_error_base('USE_APPLICATION_SERVER')


    def test_error_with_experiment_setup_section_start(self):
        self.util_test_error_base('BEGIN_EXPERIMENT_SETUP')


    def test_error_with_experiment_setup_section_setting(self):
        self.util_test_error_base('GOAL_NAME')


    def test_error_with_experiment_setup_section_end(self):
        self.util_test_error_base('END_EXPERIMENT_SETUP')


    def test_error_with_instrument(self):
        self.util_test_error_base('USE_INSTRUMENT')


    def test_error_with_instrument_setup_section_start(self):
        self.util_test_error_base('BEGIN_INSTRUMENT_SETUP')


    def test_error_with_instrument_setup_section_setting(self):
        self.util_test_error_base('INSTRUMENT_TEST')


    def test_error_with_instrument_setup_section_end(self):
        self.util_test_error_base('END_INSTRUMENT_SETUP')


    def test_error_with_predictor_model(self):
        self.util_test_error_base('USE_PREDICTOR_MODEL', model='blah', internal_data='glop')


    def test_error_with_predictor_internal_data(self):
        self.util_test_error_base('USE_PREDICTOR_INTERNAL_DATA', model='blah', internal_data='glop')


    def test_error_with_predictor_using_model(self):
        self.util_test_error_base('USE_PREDICTOR', model='blah', internal_data='glop')


    def test_error_with_predictor_no_model(self):
        self.util_test_error_base('USE_PREDICTOR')


    def test_error_with_predictor_setup_section_start(self):
        self.util_test_error_base('BEGIN_PREDICTOR_SETUP')


    def test_error_with_predictor_setup_section_setting(self):
        self.util_test_error_base('PREDICTOR_TEST')


    def test_error_with_predictor_setup_section_end(self):
        self.util_test_error_base('END_PREDICTOR_SETUP')


    def test_error_with_heuristics_repository(self):
        self.util_test_error_base('USE_HEURISTICS_REPOSITORY')


    def test_error_with_heuristic(self):
        self.util_test_error_base('USE_HEURISTIC')


    def test_error_with_training(self):
        self.util_test_error_base('TRAIN_PREDICTOR')


    def test_error_with_test(self):
        self.util_test_error_base('TEST_PREDICTOR')


    def test_error_with_data_report(self):
        self.util_test_error_base('REPORT_DATA')



class ExperimentLauncherGoalPlanningPublicExperimentsFailureTestCase(ExperimentLauncherGoalPlanningFailureTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPublicExperimentsFailureTestCase, self).setUp()
        self.experiment_type = Configuration.PUBLIC


    def util_post_test(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('EVT_PUBLIC_EXPERIMENT_FAILED', m.name)
        self.assertEqual(self.experiment.id, m.parameters[0])


class ExperimentLauncherGoalPlanningPrivateExperimentsFailureTestCase(ExperimentLauncherGoalPlanningFailureTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPrivateExperimentsFailureTestCase, self).setUp()
        self.experiment_type = Configuration.PRIVATE


class ExperimentLauncherGoalPlanningConsortiumExperimentsFailureTestCase(ExperimentLauncherGoalPlanningFailureTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningConsortiumExperimentsFailureTestCase, self).setUp()
        self.experiment_type = Configuration.CONSORTIUM


class ExperimentLauncherGoalPlanningContestBaseExperimentsFailureTestCase(ExperimentLauncherGoalPlanningFailureTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestBaseExperimentsFailureTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_BASE


class ExperimentLauncherGoalPlanningContestEntryExperimentsFailureTestCase(ExperimentLauncherGoalPlanningFailureTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestEntryExperimentsFailureTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_ENTRY



class ExperimentLauncherGoalPlanningSuccessTestCase(ExperimentLauncherGoalPlanningBaseTestCase):

    def util_createPredictorModel(self, model=None, internal_data=None):
        if model is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_MODEL', 'test.model')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.model'), 'w')
            outFile.write(model)
            outFile.close()

        if internal_data is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_INTERNAL_DATA', 'test.internal')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.internal'), 'w')
            outFile.write(internal_data)
            outFile.close()


    def util_test_base(self, model=None, internal_data=None):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment(self.experiment_type, seeds=self.seeds)
        self.util_createPredictorModel(model, internal_data)

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())
        self.assertEqual(0, Notification.objects.count())

        MockExperimentServerListener.FAIL_CONDITION          = None
        MockExperimentServerListener.ERROR_REPORT            = None
        MockExperimentServerListener.ERROR_REPORT_PARAMETERS = None
        MockExperimentServerListener.ERROR_REPORT_CONTEXT    = None
        MockExperimentServerListener.ERROR_REPORT_STACKTRACE = None

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())
        self.assertEqual(0, Alert.objects.count())

        experiment = Experiment.objects.get(id=self.experiment.id)
        self.assertEqual(Experiment.STATUS_DONE, experiment.status)

        self.assertTrue(experiment.goalplanning_results is not None)
        gpresults = GoalPlanningResult.objects.get(experiment= experiment.id)
        self.assertEqual(1, experiment.goalplanning_results.count())
        self.assertEqual(3, gpresults.goalplanning_rounds.count())
            
        self.assertTrue(experiment.data_report is not None)
        
        if self.experiment_type == Configuration.PUBLIC:
            m = self.task.out_channel.waitMessage()
            self.assertEqual('EVT_PUBLIC_EXPERIMENT_DONE', m.name)
            self.assertEqual(self.experiment.id, m.parameters[0])

        elif self.experiment_type == Configuration.CONTEST_ENTRY:
            m = self.task.out_channel.waitMessage()
            self.assertEqual('RANK_CONTEST_ENTRIES', m.name)
            self.assertEqual(self.experiment.configuration.contest.id, m.parameters[0])

        elif self.experiment_type == Configuration.CONTEST_BASE:
            self.assertEqual(2, Configuration.objects.count())
            self.assertEqual(1, Configuration.objects.filter(name='config1').count())

            config = Configuration.objects.get(name='config1')
            self.assertEqual(Configuration.CONTEST_ENTRY, config.experiment_type)
            self.assertEqual(Configuration.CUSTOM_HEURISTICS_LIST, config.heuristics)

            nb_additional_settings = 0
            if (model is None) and (internal_data is None):
                nb_additional_settings = 1
            elif (model is not None) and (internal_data is not None):
                nb_additional_settings = -1

            self.assertEqual(self.experiment.configuration.task, config.task)
            self.assertEqual(self.experiment.configuration.settings.count() + nb_additional_settings, config.settings.count())
            self.assertEqual(self.experiment.configuration.instruments_set.count(), config.instruments_set.count())
            self.assertEqual(self.experiment.configuration.heuristics_set.count() - 1, config.heuristics_set.count())
            self.assertTrue(config.heuristics_set.get(heuristic__name='heuristic1') is not None)
            self.assertTrue(config.heuristics_set.get(heuristic__name='heuristic2') is not None)

            try:
                experiment = config.experiment
                self.assertTrue(False)
            except:
                pass
    
    
    def test_simple_experiment(self):
        self.util_test_base()


    def test_model_loading(self):
        self.util_test_base(model='blah', internal_data='glop')


    def test_model_loading_no_internal_data(self):
        self.util_test_base(model='blah')


class ExperimentLauncherGoalPlanningPublicExperimentsSuccessTestCase(ExperimentLauncherGoalPlanningSuccessTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPublicExperimentsSuccessTestCase, self).setUp()
        self.experiment_type = Configuration.PUBLIC


class ExperimentLauncherGoalPlanningPrivateExperimentsSuccessTestCase(ExperimentLauncherGoalPlanningSuccessTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPrivateExperimentsSuccessTestCase, self).setUp()
        self.experiment_type = Configuration.PRIVATE


class ExperimentLauncherGoalPlanningConsortiumExperimentsSuccessTestCase(ExperimentLauncherGoalPlanningSuccessTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningConsortiumExperimentsSuccessTestCase, self).setUp()
        self.experiment_type = Configuration.CONSORTIUM


class ExperimentLauncherGoalPlanningContestBaseExperimentsSuccessTestCase(ExperimentLauncherGoalPlanningSuccessTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestBaseExperimentsSuccessTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_BASE


class ExperimentLauncherGoalPlanningContestEntryExperimentsSuccessTestCase(ExperimentLauncherGoalPlanningSuccessTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestEntryExperimentsSuccessTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_ENTRY



class ExperimentLauncherGoalPlanningPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningBaseTestCase):

    def util_test_base(self, fail_condition, error_report=None, error_report_parameters=None,
                       error_report_context=None, error_report_stacktrace=None,
                       experiment_will_succeed=True):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment(self.experiment_type, seeds=self.seeds)

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())
        self.assertEqual(0, Notification.objects.count())
        self.assertEqual(0, PluginErrorReport.objects.count())

        MockExperimentServerListener.FAIL_CONDITION          = fail_condition
        MockExperimentServerListener.ERROR_REPORT            = error_report
        MockExperimentServerListener.ERROR_REPORT_PARAMETERS = error_report_parameters
        MockExperimentServerListener.ERROR_REPORT_CONTEXT    = error_report_context
        MockExperimentServerListener.ERROR_REPORT_STACKTRACE = error_report_stacktrace

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())

        if experiment_will_succeed:
            self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())
            self.assertEqual(0, Alert.objects.count())
        else:
            self.assertEqual(1, Job.objects.filter(status=Job.STATUS_FAILED).count())
            self.assertEqual(1, Alert.objects.count())

        self.assertEqual(1, PluginErrorReport.objects.count())

        experiment = Experiment.objects.get(id=self.experiment.id)

        if experiment_will_succeed:
            self.assertEqual(Experiment.STATUS_DONE_WITH_ERRORS, experiment.status)
            gpresults = GoalPlanningResult.objects.get(experiment= experiment.id)
            self.assertEqual(1, experiment.goalplanning_results.count())
            self.assertEqual(3, gpresults.goalplanning_rounds.count())
            self.assertTrue(experiment.data_report is not None)
        else:
            self.assertEqual(Experiment.STATUS_FAILED, experiment.status)

        if self.experiment_type == Configuration.PUBLIC:
            m = self.task.out_channel.waitMessage()

            if experiment_will_succeed:
                self.assertEqual('EVT_PUBLIC_EXPERIMENT_DONE', m.name)
            else:
                self.assertEqual('EVT_PUBLIC_EXPERIMENT_FAILED', m.name)

            self.assertEqual(self.experiment.id, m.parameters[0])

        elif self.experiment_type == Configuration.CONTEST_BASE:
            if experiment_will_succeed:
                self.assertEqual(2, Configuration.objects.count())
                self.assertEqual(1, Configuration.objects.filter(name='config1').count())

                config = Configuration.objects.get(name='config1')
                self.assertEqual(Configuration.CONTEST_ENTRY, config.experiment_type)
                self.assertEqual(Configuration.CUSTOM_HEURISTICS_LIST, config.heuristics)

                self.assertEqual(self.experiment.configuration.task, config.task)
                self.assertEqual(self.experiment.configuration.settings.count() + 1, config.settings.count())
                self.assertEqual(self.experiment.configuration.instruments_set.count(), config.instruments_set.count())
                self.assertEqual(self.experiment.configuration.heuristics_set.count() - 1, config.heuristics_set.count())
                self.assertTrue(config.heuristics_set.get(heuristic__name='heuristic1') is not None)
                self.assertTrue(config.heuristics_set.get(heuristic__name='heuristic2') is not None)

                try:
                    experiment = config.experiment
                    self.assertTrue(False)
                except:
                    pass
            else:
                self.assertEqual(1, Configuration.objects.count())


    def test_instrument_crash(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='INSTRUMENT_CRASH',
                            error_report_parameters=['user1/instrument1'],
                            error_report_context='some context',
                            error_report_stacktrace='some stacktrace',
                            experiment_will_succeed=(self.experiment_type != Configuration.EVALUATION))

        self.assertEqual(1, Instrument.objects.filter(status=Instrument.DISABLED).count())
        self.assertEqual(1, Instrument.objects.filter(status=Instrument.ENABLED).count())
        self.assertEqual('instrument1', Instrument.objects.get(status=Instrument.DISABLED).name)

        self.assertEqual(1, Instrument.objects.get(status=Instrument.DISABLED).error_reports.count())

        error_report = Instrument.objects.get(status=Instrument.DISABLED).error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('some stacktrace', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_instrument_error(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='INSTRUMENT_ERROR',
                            error_report_parameters=['user1/instrument1', 'Something went wrong'],
                            error_report_context='some context',
                            experiment_will_succeed=(self.experiment_type != Configuration.EVALUATION))

        self.assertEqual(1, Instrument.objects.filter(status=Instrument.DISABLED).count())
        self.assertEqual(1, Instrument.objects.filter(status=Instrument.ENABLED).count())
        self.assertEqual('instrument1', Instrument.objects.get(status=Instrument.DISABLED).name)

        self.assertEqual(1, Instrument.objects.get(status=Instrument.DISABLED).error_reports.count())

        error_report = Instrument.objects.get(status=Instrument.DISABLED).error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_heuristic_crash(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='HEURISTIC_CRASH',
                            error_report_parameters=['user1/heuristic1'],
                            error_report_context='some context',
                            error_report_stacktrace='some stacktrace',
                            experiment_will_succeed=((self.experiment_type != Configuration.EVALUATION) and \
                                                     (self.experiment_type != Configuration.CONTEST_ENTRY)))

        self.assertEqual(1, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_DISABLED).count())
        self.assertEqual(2, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_OK).count())
        self.assertEqual('heuristic1', HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).heuristic.name)

        self.assertEqual(1, HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.count())

        error_report = HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('some stacktrace', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_heuristic_timeout(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='HEURISTIC_TIMEOUT',
                            error_report_parameters=['user1/heuristic1'],
                            error_report_context='some context',
                            experiment_will_succeed=((self.experiment_type != Configuration.EVALUATION) and \
                                                     (self.experiment_type != Configuration.CONTEST_ENTRY)))

        self.assertEqual(1, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_DISABLED).count())
        self.assertEqual(2, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_OK).count())
        self.assertEqual('heuristic1', HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).heuristic.name)

        self.assertEqual(1, HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.count())

        error_report = HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_heuristic_error(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='HEURISTIC_ERROR',
                            error_report_parameters=['user1/heuristic1', 'Something went wrong'],
                            error_report_context='some context',
                            experiment_will_succeed=((self.experiment_type != Configuration.EVALUATION) and \
                                                     (self.experiment_type != Configuration.CONTEST_ENTRY)))

        self.assertEqual(1, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_DISABLED).count())
        self.assertEqual(2, HeuristicVersion.objects.filter(status=HeuristicVersion.STATUS_OK).count())
        self.assertEqual('heuristic1', HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).heuristic.name)

        self.assertEqual(1, HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.count())

        error_report = HeuristicVersion.objects.get(status=HeuristicVersion.STATUS_DISABLED).error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_predictor_crash(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='PREDICTOR_CRASH',
                            error_report_context='some context',
                            error_report_stacktrace='some stacktrace',
                            experiment_will_succeed=False)

        # This feature was disabled
        # self.assertEqual(1, Goalplanner.objects.filter(status=Goalplanner.EXPERIMENTAL).count())
        # self.assertEqual(0, Goalplanner.objects.filter(status=Goalplanner.ENABLED).count())
        # self.assertEqual('predictor1', Goalplanner.objects.get(status=Goalplanner.EXPERIMENTAL).name)

        self.assertEqual(1, Goalplanner.objects.get(name='predictor1').error_reports.count())

        error_report = Goalplanner.objects.get(name='predictor1').error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('some stacktrace', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


    def test_predictor_error(self):
        self.util_test_base('TRAIN_PREDICTOR',
                            error_report='PREDICTOR_ERROR',
                            error_report_parameters=['Something went wrong'],
                            error_report_context='some context',
                            experiment_will_succeed=False)

        # This feature was disabled
        # self.assertEqual(1, Goalplanner.objects.filter(status=Goalplanner.EXPERIMENTAL).count())
        # self.assertEqual(0, Goalplanner.objects.filter(status=Goalplanner.ENABLED).count())
        # self.assertEqual('predictor1', Goalplanner.objects.get(status=Goalplanner.EXPERIMENTAL).name)

        self.assertEqual(1, Goalplanner.objects.get(name='predictor1').error_reports.count())

        error_report = Goalplanner.objects.get(name='predictor1').error_reports.all()[0]

        self.assertEqual('some context', error_report.context)
        self.assertEqual('', error_report.stacktrace)
        self.assertEqual(self.experiment, error_report.experiment)


class ExperimentLauncherGoalPlanningPublicExperimentsPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningPluginErrorReportsTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPublicExperimentsPluginErrorReportsTestCase, self).setUp()
        self.experiment_type = Configuration.PUBLIC


class ExperimentLauncherGoalPlanningPrivateExperimentsPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningPluginErrorReportsTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPrivateExperimentsPluginErrorReportsTestCase, self).setUp()
        self.experiment_type = Configuration.PRIVATE


class ExperimentLauncherGoalPlanningConsortiumExperimentsPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningPluginErrorReportsTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningConsortiumExperimentsPluginErrorReportsTestCase, self).setUp()
        self.experiment_type = Configuration.CONSORTIUM


class ExperimentLauncherGoalPlanningContestBaseExperimentsPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningPluginErrorReportsTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestBaseExperimentsPluginErrorReportsTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_BASE


class ExperimentLauncherGoalPlanningContestEntryExperimentsPluginErrorReportsTestCase(ExperimentLauncherGoalPlanningPluginErrorReportsTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestEntryExperimentsPluginErrorReportsTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_ENTRY



class ExperimentLauncherGoalPlanningCancellingTestCase(ExperimentLauncherGoalPlanningBaseTestCase):

    def util_createPredictorModel(self, model=None, internal_data=None):
        if model is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_MODEL', 'test.model')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.model'), 'w')
            outFile.write(model)
            outFile.close()

        if internal_data is not None:
            self.experiment.configuration.addSetting('USE_PREDICTOR_INTERNAL_DATA', 'test.internal')
            outFile = open(os.path.join(settings.MODELS_ROOT, 'test.internal'), 'w')
            outFile.write(internal_data)
            outFile.close()


    def util_test_cancelling_base(self, cancel_condition, model=None, internal_data=None):
        self.util_createApplicationServer()
        self.util_createExperimentServer()
        self.util_start()
        self.util_createExperiment(self.experiment_type)
        self.util_createPredictorModel(model, internal_data)

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(0, GoalPlanningResult.objects.count())
        self.assertEqual(0, Notification.objects.count())

        self.cancel_condition = cancel_condition

        MockExperimentServerListener.FAIL_CONDITION          = None
        MockExperimentServerListener.ERROR_REPORT            = None
        MockExperimentServerListener.ERROR_REPORT_PARAMETERS = None
        MockExperimentServerListener.ERROR_REPORT_CONTEXT    = None
        MockExperimentServerListener.ERROR_REPORT_STACKTRACE = None

        self.task.processMessage(Message('RUN_EXPERIMENT', [self.experiment.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_CANCELLED).count())
        self.assertEqual(0, Alert.objects.count())

        experiment = Experiment.objects.get(id=self.experiment.id)
        self.assertEqual(Experiment.STATUS_FAILED, experiment.status)

        self.assertEqual(cancel_condition, MockExperimentServerListener.LAST_COMMAND.name)

        m = self.task.out_channel.waitMessage()
        self.assertEqual('EVT_EXPERIMENT_CANCELLED', m.name)
        self.assertEqual(self.experiment.id, m.parameters[0])


    def util_wait_jobs_completion_listener(self):
        if MockExperimentServerListener.LAST_COMMAND.name == self.cancel_condition:
            self.task.processMessage(Message('CANCEL_EXPERIMENT', [self.experiment.id]))


    def test_cancelling_at_experiment_type(self):
        self.util_test_cancelling_base('SET_EXPERIMENT_TYPE')


    def test_cancelling_at_application_server(self):
        self.util_test_cancelling_base('USE_APPLICATION_SERVER')


    def test_cancelling_at_experiment_setup_section_start(self):
        self.util_test_cancelling_base('BEGIN_EXPERIMENT_SETUP')


    def test_cancelling_at_experiment_setup_section_setting(self):
        self.util_test_cancelling_base('GOAL_NAME')


    def test_cancelling_at_experiment_setup_section_end(self):
        self.util_test_cancelling_base('END_EXPERIMENT_SETUP')


    def test_cancelling_at_instrument(self):
        self.util_test_cancelling_base('USE_INSTRUMENT')


    def test_cancelling_at_instrument_setup_section_start(self):
        self.util_test_cancelling_base('BEGIN_INSTRUMENT_SETUP')


    def test_cancelling_at_instrument_setup_section_setting(self):
        self.util_test_cancelling_base('INSTRUMENT_TEST')


    def test_cancelling_at_instrument_setup_section_end(self):
        self.util_test_cancelling_base('END_INSTRUMENT_SETUP')


    def test_cancelling_at_predictor_model(self):
        self.util_test_cancelling_base('USE_PREDICTOR_MODEL', model='blah', internal_data='glop')


    def test_cancelling_at_predictor_internal_data(self):
        self.util_test_cancelling_base('USE_PREDICTOR_INTERNAL_DATA', model='blah', internal_data='glop')


    def test_cancelling_at_predictor_using_model(self):
        self.util_test_cancelling_base('USE_PREDICTOR', model='blah', internal_data='glop')


    def test_cancelling_at_predictor_no_model(self):
        self.util_test_cancelling_base('USE_PREDICTOR')


    def test_cancelling_at_predictor_setup_section_start(self):
        self.util_test_cancelling_base('BEGIN_PREDICTOR_SETUP')


    def test_cancelling_at_predictor_setup_section_setting(self):
        self.util_test_cancelling_base('PREDICTOR_TEST')


    def test_cancelling_at_predictor_setup_section_end(self):
        self.util_test_cancelling_base('END_PREDICTOR_SETUP')


    def test_cancelling_at_heuristics_repository(self):
        self.util_test_cancelling_base('USE_HEURISTICS_REPOSITORY')


    def test_cancelling_at_heuristic(self):
        self.util_test_cancelling_base('USE_HEURISTIC')


    def test_cancelling_at_training(self):
        self.util_test_cancelling_base('TRAIN_PREDICTOR')


    def test_cancelling_at_test(self):
        self.util_test_cancelling_base('TEST_PREDICTOR')


    def test_cancelling_at_data_report(self):
        self.util_test_cancelling_base('REPORT_DATA')


class ExperimentLauncherGoalPlanningPublicExperimentsCancellingTestCase(ExperimentLauncherGoalPlanningCancellingTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPublicExperimentsCancellingTestCase, self).setUp()
        self.experiment_type = Configuration.PUBLIC


class ExperimentLauncherGoalPlanningPrivateExperimentsCancellingTestCase(ExperimentLauncherGoalPlanningCancellingTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningPrivateExperimentsCancellingTestCase, self).setUp()
        self.experiment_type = Configuration.PRIVATE


class ExperimentLauncherGoalPlanningConsortiumExperimentsCancellingTestCase(ExperimentLauncherGoalPlanningCancellingTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningConsortiumExperimentsCancellingTestCase, self).setUp()
        self.experiment_type = Configuration.CONSORTIUM


class ExperimentLauncherGoalPlanningContestBaseExperimentsCancellingTestCase(ExperimentLauncherGoalPlanningCancellingTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestBaseExperimentsCancellingTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_BASE


class ExperimentLauncherGoalPlanningContestEntryExperimentsCancellingTestCase(ExperimentLauncherGoalPlanningCancellingTestCase):

    def setUp(self):
        super(ExperimentLauncherGoalPlanningContestEntryExperimentsCancellingTestCase, self).setUp()
        self.experiment_type = Configuration.CONTEST_ENTRY



def tests():
    return [ ExperimentLauncherGoalPlanningServersTestCase,
             ExperimentLauncherGoalPlanningPublicExperimentsFailureTestCase,
             ExperimentLauncherGoalPlanningPrivateExperimentsFailureTestCase,
             ExperimentLauncherGoalPlanningConsortiumExperimentsFailureTestCase,
             ExperimentLauncherGoalPlanningContestBaseExperimentsFailureTestCase,
             ExperimentLauncherGoalPlanningContestEntryExperimentsFailureTestCase,
             ExperimentLauncherGoalPlanningPublicExperimentsSuccessTestCase,
             ExperimentLauncherGoalPlanningPrivateExperimentsSuccessTestCase,
             ExperimentLauncherGoalPlanningConsortiumExperimentsSuccessTestCase,
             ExperimentLauncherGoalPlanningContestBaseExperimentsSuccessTestCase,
             ExperimentLauncherGoalPlanningContestEntryExperimentsSuccessTestCase,
             ExperimentLauncherGoalPlanningPublicExperimentsPluginErrorReportsTestCase,
             ExperimentLauncherGoalPlanningPrivateExperimentsPluginErrorReportsTestCase,
             ExperimentLauncherGoalPlanningConsortiumExperimentsPluginErrorReportsTestCase,
             ExperimentLauncherGoalPlanningContestBaseExperimentsPluginErrorReportsTestCase,
             ExperimentLauncherGoalPlanningContestEntryExperimentsPluginErrorReportsTestCase,
             ExperimentLauncherGoalPlanningPublicExperimentsCancellingTestCase,
             ExperimentLauncherGoalPlanningPrivateExperimentsCancellingTestCase,
             ExperimentLauncherGoalPlanningConsortiumExperimentsCancellingTestCase,
             ExperimentLauncherGoalPlanningContestBaseExperimentsCancellingTestCase,
             ExperimentLauncherGoalPlanningContestEntryExperimentsCancellingTestCase,
           ]

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


from base_task_test import BaseTaskTest
from implemented_tasks.experiment_launcher import ExperimentLauncher
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.models import HeuristicEvaluationResults
from mash.heuristics.models import HeuristicEvaluationStep
from mash.instruments.models import Instrument
from mash.instruments.models import DataReport
from mash.servers.models import Server
from mash.servers.models import Job
from mash.servers.models import Alert
from mash.experiments.models import Experiment
from mash.experiments.models import Configuration
from mash.experiments.models import ClassificationResults
from mash.experiments.models import GoalPlanningResult
from mash.experiments.models import Notification
from mash.tasks.models import Task as DBTask
from mash.tasks.models import Database
from mash.tools.models import PluginErrorReport
from mash.contests.models import Contest
from mash.goalplanners.models import Goalplanner
from mash.classifiers.models import Classifier
from mocks.mock_server_listeners import MockExperimentServerListener
from mocks.mock_server_listeners import MockImageServerListener
from pymash.messages import Message
from pymash.gitrepository import GitRepository
from pymash.server import ThreadedServer
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
from datetime import datetime
import time
import os
import shutil


class BaseExperimentLauncherTest(BaseTaskTest):

    def setUp(self):
        self.experiment         = None
        self.experiment_server  = None
        self.application_server = None
        self.task               = None
        self.heuristicsRepo     = None

        self.tearDown()
        
        os.makedirs(settings.MODELS_ROOT)
        os.makedirs(settings.DATA_REPORTS_ROOT)


    def tearDown(self):
        if self.task is not None:
            del self.task

        if self.experiment_server is not None:
            self.experiment_server.stop()

        if self.application_server is not None:
            self.application_server.stop()

        PluginErrorReport.objects.all().delete()
        HeuristicEvaluationStep.objects.all().delete()
        HeuristicTestStatus.objects.all().delete()
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        User.objects.all().delete()
        Alert.objects.all().delete()
        Job.objects.all().delete()
        Server.objects.all().delete()
        Configuration.objects.all().delete()
        Experiment.objects.all().delete()
        ClassificationResults.objects.all().delete()
        GoalPlanningResult.objects.all().delete()
        Notification.objects.all().delete()
        DBTask.objects.all().delete()
        Database.objects.all().delete()
        Instrument.objects.all().delete()
        DataReport.objects.all().delete()
        Contest.objects.all().delete()
        Goalplanner.objects.all().delete()
        Classifier.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')

        if self.heuristicsRepo is not None:
            self.heuristicsRepo.delete()
            del self.heuristicsRepo

        if os.path.exists(settings.REPOSITORIES_ROOT):
            shutil.rmtree(settings.REPOSITORIES_ROOT)

        if os.path.exists(settings.MODELS_ROOT):
            shutil.rmtree(settings.MODELS_ROOT)

        if os.path.exists(settings.DATA_REPORTS_ROOT):
            shutil.rmtree(settings.DATA_REPORTS_ROOT)

    
    def util_createExperimentServer(self, restrict_experiment=None):
        server                      = Server()
        server.name                 = 'Experimentix'
        server.address              = '127.0.0.1'
        server.port                 = 18000
        server.server_type          = Server.EXPERIMENTS_SERVER
        server.subtype              = Server.SUBTYPE_NONE
        server.restrict_experiment  = restrict_experiment
        server.status               = Server.SERVER_STATUS_ONLINE
        server.save()

        server.supported_tasks.add(DBTask.objects.all()[0])


    def util_create_heuristic(self, user_name='user1', heuristic_name='heuristic1'):
        try:
            user = User.objects.get(username=user_name)
        except:
            user = User()
            user.username = user_name
            user.save()

        heuristic = Heuristic()
        heuristic.name = heuristic_name
        heuristic.author = user
        heuristic.save()

        heuristic_version = HeuristicVersion()
        heuristic_version.heuristic = heuristic
        heuristic_version.version = 1
        heuristic_version.filename = '%s.cpp' % heuristic_name
        heuristic_version.upload_date = datetime.now()
        heuristic_version.checked = True
        heuristic_version.save()

        if not(os.path.exists(settings.REPOSITORIES_ROOT)):
            os.makedirs(settings.REPOSITORIES_ROOT)

        self.heuristicsRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
        self.heuristicsRepo.createIfNotExists()

        fullpath = os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS, user_name, '%s.cpp' % heuristic_name)
        if not(os.path.exists(fullpath)):
            os.makedirs(os.path.dirname(fullpath))
            outFile = open(fullpath, 'w')
            outFile.write('TEST')
            outFile.close()
            self.heuristicsRepo.commitFile('%s/%s.cpp' % (user_name, heuristic_name),
                                           'Add the test heuristic', settings.COMMIT_AUTHOR)
        
        return heuristic_version


    def util_create_instrument(self, user_name='user1', instrument_name='instrument1'):
        try:
            user = User.objects.get(username=user_name)
        except:
            user = User()
            user.username = user_name
            user.save()

        instrument = Instrument()
        instrument.name = instrument_name
        instrument.author = user
        instrument.status = Instrument.ENABLED
        instrument.save()

        return instrument


    def util_start(self, no_experiment_server=False, no_application_server=False):
        try:
            if not(no_experiment_server):
                server = Server.objects.get(server_type=Server.EXPERIMENTS_SERVER)
                self.experiment_server = ThreadedServer(server.address, server.port, MockExperimentServerListener)
                self.experiment_server.start()
        except:
            pass

        try:
            if not(no_application_server):
                server = Server.objects.get(server_type=Server.APPLICATION_SERVER)
                self.application_server = ThreadedServer(server.address, server.port, MockImageServerListener)
                self.application_server.start()
        except:
            pass

        if (self.experiment_server is not None) or (self.application_server is not None):
            time.sleep(1)
        
        self.task = ExperimentLauncher()
        self.task.start()

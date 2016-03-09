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
from implemented_tasks.heuristic_checker import HeuristicChecker
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.servers.models import Server
from mash.servers.models import Job
from mash.servers.models import Alert
from mash.tools.models import PluginErrorReport
from mocks.mock_server_listeners import MockCompilationServerListener
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


class HeuristicCheckerBaseTestCase(BaseTaskTest):

    def setUp(self):
        HeuristicTestStatus.objects.all().delete()
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        User.objects.all().delete()
        Alert.objects.all().delete()
        Job.objects.all().delete()
        Server.objects.all().delete()

        server             = Server()
        server.name        = 'Compilox'
        server.address     = '127.0.0.1'
        server.port        = 18000
        server.server_type = Server.COMPILATION_SERVER
        server.subtype     = Server.SUBTYPE_NONE
        server.status      = Server.SERVER_STATUS_ONLINE
        server.save()

        MockCompilationServerListener.FAIL_CONDITION = None

        self.server = None
        self.task = None
        self.uploadRepo = None
        self.heuristicsRepo = None


    def tearDown(self):
        if self.task is not None:
            del self.task

        if self.server is not None:
            self.server.stop()

        HeuristicTestStatus.objects.all().delete()
        HeuristicVersion.objects.all().delete()
        Heuristic.objects.all().delete()
        User.objects.all().delete()
        Alert.objects.all().delete()
        Job.objects.all().delete()
        Server.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')

        if self.uploadRepo is not None:
            self.uploadRepo.delete()
            del self.uploadRepo

        if self.heuristicsRepo is not None:
            self.heuristicsRepo.delete()
            del self.heuristicsRepo

        if os.path.exists(settings.REPOSITORIES_ROOT):
            shutil.rmtree(settings.REPOSITORIES_ROOT)

    
    def util_start(self):
        self.server = ThreadedServer('127.0.0.1', 18000, MockCompilationServerListener)
        self.server.start()
        time.sleep(1)

        self.task = HeuristicChecker()
        self.task.start()


    def util_create_heuristic(self):
        user = User()
        user.username = 'user1'
        user.save()
        
        heuristic = Heuristic()
        heuristic.name = 'heuristic1'
        heuristic.author = user
        heuristic.save()
        
        self.heuristic_version = HeuristicVersion()
        self.heuristic_version.heuristic = heuristic
        self.heuristic_version.version = 1
        self.heuristic_version.filename = 'heuristic1.cpp'
        self.heuristic_version.upload_date = datetime.now()
        self.heuristic_version.save()
        
        if not(os.path.exists(settings.REPOSITORIES_ROOT)):
            os.makedirs(settings.REPOSITORIES_ROOT)
        
        self.uploadRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
        self.uploadRepo.createIfNotExists()

        fullpath = os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD, 'user1', 'heuristic1.cpp')
        if not(os.path.exists(fullpath)):
            os.makedirs(os.path.dirname(fullpath))
            outFile = open(fullpath, 'w')
            outFile.write('TEST')
            outFile.close()
            self.uploadRepo.commitFile('user1/heuristic1.cpp', 'Add the test heuristic', settings.COMMIT_AUTHOR)

        self.heuristicsRepo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
        self.heuristicsRepo.createIfNotExists()


    def util_test_error_base(self, fail_condition, phase):
        self.assertEqual(0, Job.objects.count())
        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        MockCompilationServerListener.FAIL_CONDITION = fail_condition

        if self.task is None:
            self.util_start()
        else:
            self.task.processMessage(Message('CHECK_HEURISTIC', [self.heuristic_version.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_FAILED).count())

        self.assertEqual(1, Alert.objects.count())

        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(1, HeuristicTestStatus.objects.count())
        self.assertEqual(phase, HeuristicTestStatus.objects.get(heuristic_version=self.heuristic_version).phase)
        self.assertTrue(HeuristicTestStatus.objects.get(heuristic_version=self.heuristic_version).error)

        self.assertTrue(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.uploadRepo))
        self.assertFalse(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.heuristicsRepo))

    
    def util_is_heuristic_version_in_repository(self, heuristic_version, repository):
        try:
            blob = repository.repository().tree()[heuristic_version.heuristic.author.username.lower()][heuristic_version.filename]
            return True
        except:
            return False
        


class HeuristicCheckerStartupTestCase(HeuristicCheckerBaseTestCase):

    def test_no_heuristic_to_check(self):
        self.util_start()
        self.assertEqual(0, Job.objects.count())


    def test_successful_check(self):
        self.util_create_heuristic()
        
        self.assertEqual(0, Job.objects.count())
        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.util_start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(0, Alert.objects.count())

        self.assertTrue(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.assertFalse(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.uploadRepo))
        self.assertTrue(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.heuristicsRepo))

        m = self.task.out_channel.waitMessage()
        self.assertEqual('EVT_HEURISTIC_CHECKED', m.name)
        self.assertEqual(self.heuristic_version.id, m.parameters[0])


    def test_no_server_available(self):
        self.util_create_heuristic()
        
        self.assertEqual(0, Job.objects.count())
        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        MockCompilationServerListener.FAIL_CONDITION = 'STATUS'

        self.util_start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())

        self.assertEqual(0, Alert.objects.count())

        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.assertTrue(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.uploadRepo))
        self.assertFalse(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.heuristicsRepo))


    def test_error_with_heuristics_repository(self):
        self.util_create_heuristic()
        self.util_test_error_base('USE_HEURISTICS_REPOSITORY', HeuristicTestStatus.PHASE_STATUS)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_error_during_compilation(self):
        self.util_create_heuristic()
        self.util_test_error_base('COMPILATION__ERROR', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_compilation_error(self):
        self.util_create_heuristic()
        self.util_test_error_base('COMPILATION__COMPILATION_ERROR', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_unknown_response_during_compilation(self):
        self.util_create_heuristic()
        self.util_test_error_base('COMPILATION__UNKNOWN', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_analysis_error(self):
        self.util_create_heuristic()
        self.util_test_error_base('ANALYSIS__ANALYZE_ERROR', HeuristicTestStatus.PHASE_ANALYZE)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_unknown_response_during_analysis(self):
        self.util_create_heuristic()
        self.util_test_error_base('ANALYSIS__UNKNOWN', HeuristicTestStatus.PHASE_ANALYZE)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_test_error(self):
        self.util_create_heuristic()
        self.util_test_error_base('TEST__TEST_ERROR', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) == 0)


    def test_heuristic_crash(self):
        self.util_create_heuristic()
        self.util_test_error_base('TEST__HEURISTIC_CRASH', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) == 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) > 0)


    def test_heuristic_timeout(self):
        self.util_create_heuristic()
        self.util_test_error_base('TEST__HEURISTIC_TIMEOUT', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) == 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) == 0)


    def test_unknown_response_during_test(self):
        self.util_create_heuristic()
        self.util_test_error_base('TEST__UNKNOWN', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(0, PluginErrorReport.objects.count())


class HeuristicCheckerTestCase(HeuristicCheckerBaseTestCase):

    def setUp(self):
        super(HeuristicCheckerTestCase, self).setUp()
        self.util_start()
        self.util_create_heuristic()


    def test_successful_check(self):
        self.assertEqual(0, Job.objects.count())
        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.task.processMessage(Message('CHECK_HEURISTIC', [self.heuristic_version.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())

        self.assertEqual(0, Alert.objects.count())

        self.assertTrue(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.assertFalse(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.uploadRepo))
        self.assertTrue(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.heuristicsRepo))
        
        m = self.task.out_channel.waitMessage()
        self.assertEqual('EVT_HEURISTIC_CHECKED', m.name)
        self.assertEqual(self.heuristic_version.id, m.parameters[0])


    def test_no_server_available(self):
        self.assertEqual(0, Job.objects.count())
        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        MockCompilationServerListener.FAIL_CONDITION = 'STATUS'

        self.task.processMessage(Message('CHECK_HEURISTIC', [self.heuristic_version.id]))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DELAYED).count())

        self.assertEqual(0, Alert.objects.count())

        self.assertFalse(HeuristicVersion.objects.get(id=self.heuristic_version.id).checked)
        self.assertEqual(0, HeuristicTestStatus.objects.count())

        self.assertTrue(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.uploadRepo))
        self.assertFalse(self.util_is_heuristic_version_in_repository(HeuristicVersion.objects.get(id=self.heuristic_version.id), self.heuristicsRepo))


    def test_error_with_heuristics_repository(self):
        self.util_test_error_base('USE_HEURISTICS_REPOSITORY', HeuristicTestStatus.PHASE_STATUS)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_error_during_compilation(self):
        self.util_test_error_base('COMPILATION__ERROR', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_compilation_error(self):
        self.util_test_error_base('COMPILATION__COMPILATION_ERROR', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_unknown_response_during_compilation(self):
        self.util_test_error_base('COMPILATION__UNKNOWN', HeuristicTestStatus.PHASE_COMPILATION)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_analysis_error(self):
        self.util_test_error_base('ANALYSIS__ANALYZE_ERROR', HeuristicTestStatus.PHASE_ANALYZE)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_unknown_response_during_analysis(self):
        self.util_test_error_base('ANALYSIS__UNKNOWN', HeuristicTestStatus.PHASE_ANALYZE)
        self.assertEqual(0, PluginErrorReport.objects.count())


    def test_test_error(self):
        self.util_test_error_base('TEST__TEST_ERROR', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) == 0)


    def test_heuristic_crash(self):
        self.util_test_error_base('TEST__HEURISTIC_CRASH', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) == 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) > 0)


    def test_heuristic_timeout(self):
        self.util_test_error_base('TEST__HEURISTIC_TIMEOUT', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(1, PluginErrorReport.objects.count())
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).description) == 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).context) > 0)
        self.assertTrue(len(PluginErrorReport.objects.get(heuristic_version=self.heuristic_version).stacktrace) == 0)
    

    def test_unknown_response_during_test(self):
        self.util_test_error_base('TEST__UNKNOWN', HeuristicTestStatus.PHASE_TEST)
        self.assertEqual(0, PluginErrorReport.objects.count())



def tests():
    return [ HeuristicCheckerStartupTestCase,
             HeuristicCheckerTestCase,
           ]

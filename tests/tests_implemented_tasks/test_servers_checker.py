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
from implemented_tasks.servers_checker import ServersChecker
from mash.servers.models import Server
from mash.servers.models import Job
from pymash.server import ThreadedServer
from mocks.mock_server_listeners import MockEchoListener
import time
import os
import shutil


class ServersCheckerStartupTestCase(BaseTaskTest):

    def test_on_startup(self):
        Server.objects.all().delete()
        Job.objects.all().delete()

        for i in range(0, 3):
            server             = Server()
            server.name        = 'Server%d' % (i + 1)
            server.address     = '127.0.0.1'
            server.port        = 18000 + i
            server.server_type = Server.EXPERIMENTS_SERVER
            server.subtype     = Server.SUBTYPE_NONE
            server.status      = Server.SERVER_STATUS_UNKNOWN
            server.save()

        self.assertEqual(0, Job.objects.count())
        self.assertEqual(3, Server.objects.filter(status=Server.SERVER_STATUS_UNKNOWN).count())
        
        self.task = ServersChecker()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())
        self.assertEqual(3, Server.objects.filter(status=Server.SERVER_STATUS_OFFLINE).count())

        del self.task

        Server.objects.all().delete()
        Job.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')



class ServersCheckerTestCase(BaseTaskTest):

    def setUp(self):
        Server.objects.all().delete()
        Job.objects.all().delete()
        
        self.task = ServersChecker()
        self.task.start()

        # Avoid the startup phase
        self.util_wait_jobs_completion([self.task])

        Job.objects.all().delete()

        for i in range(0, 3):
            server             = Server()
            server.name        = 'Server%d' % (i + 1)
            server.address     = '127.0.0.1'
            server.port        = 18000 + i
            server.server_type = Server.EXPERIMENTS_SERVER
            server.subtype     = Server.SUBTYPE_NONE
            server.status      = Server.SERVER_STATUS_UNKNOWN
            server.save()

        time.sleep(3)


    def tearDown(self):
        del self.task

        Server.objects.all().delete()
        Job.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def test_no_server_online(self):
        self.assertEqual(3, Server.objects.filter(status=Server.SERVER_STATUS_UNKNOWN).count())

        self.assertTrue(self.task.processMessage('CHECK_SERVERS_STATUS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())

        job = Job.objects.all()[0]
        self.assertEqual(Job.STATUS_DONE, job.status)

        self.assertEqual(3, Server.objects.filter(status=Server.SERVER_STATUS_OFFLINE).count())


    def test_one_server_online(self):
        self.assertEqual(3, Server.objects.filter(status=Server.SERVER_STATUS_UNKNOWN).count())

        server1 = ThreadedServer('127.0.0.1', 18001, MockEchoListener)
        server1.start()
        time.sleep(1)

        self.assertTrue(self.task.processMessage('CHECK_SERVERS_STATUS'))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())

        job = Job.objects.all()[0]
        self.assertEqual(Job.STATUS_DONE, job.status)

        self.assertEqual(2, Server.objects.filter(status=Server.SERVER_STATUS_OFFLINE).count())
        self.assertEqual(1, Server.objects.filter(status=Server.SERVER_STATUS_ONLINE).count())

        self.assertEqual('Server2', Server.objects.filter(status=Server.SERVER_STATUS_ONLINE)[0].name)

        server1.stop()


def tests():
    return [ ServersCheckerStartupTestCase,
             ServersCheckerTestCase,
           ]

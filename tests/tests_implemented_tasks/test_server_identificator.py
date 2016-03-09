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
from implemented_tasks.server_identificator import ServerIdentificator
from mash.servers.models import Server
from mash.servers.models import Job
from pymash.server import ThreadedServer
from mocks.mock_server_listeners import MockCompilationServerListener
from mocks.mock_server_listeners import MockExperimentServerListener
from mocks.mock_server_listeners import MockImageServerListener
from mocks.mock_server_listeners import MockInteractiveServerListener
from pymash.messages import Message
import time
import os
import shutil


class ServerIdentificatorStartupTestCase(BaseTaskTest):

    def setUp(self):
        Server.objects.all().delete()
        Job.objects.all().delete()

        for i in range(0, 3):
            server             = Server()
            server.name        = 'Server%d' % (i + 1)
            server.address     = '127.0.0.1'
            server.port        = 18000 + i
            server.server_type = Server.UNIDENTIFIED_SERVER
            server.subtype     = Server.SUBTYPE_NONE
            server.status      = Server.SERVER_STATUS_UNKNOWN
            server.save()

        self.task = None
        self.server1 = None
        

    def tearDown(self):
        if self.task is not None:
            del self.task

        if self.server1 is not None:
            self.server1.stop()

        Server.objects.all().delete()
        Job.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def test_no_server_online(self):
        self.assertEqual(0, Job.objects.count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())
        
        self.task = ServerIdentificator()
        self.task.start()
    
        self.util_wait_jobs_completion([self.task])
    
        self.assertEqual(3, Job.objects.count())
        self.assertEqual(3, Job.objects.filter(status=Job.STATUS_DELAYED).count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())
    
    
    def util_test_identification_base(self, server_listener_class, server_type, server_subtype=None):
        self.assertEqual(0, Job.objects.count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())

        self.server1 = ThreadedServer('127.0.0.1', 18000, server_listener_class)
        self.server1.start()
        time.sleep(1)

        self.task = ServerIdentificator()
        self.task.start()

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(3, Job.objects.count())
        self.assertEqual(2, Job.objects.filter(status=Job.STATUS_DELAYED).count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())
        
        self.assertEqual(2, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())
        self.assertEqual(1, Server.objects.filter(server_type=server_type).count())

        server = Server.objects.filter(server_type=server_type)[0]

        self.assertEqual('Server1', server.name)

        if server_subtype is not None:
            self.assertEqual(server_subtype, server.subtype)


    def test_identify_experiments_server(self):
        self.util_test_identification_base(MockExperimentServerListener, Server.EXPERIMENTS_SERVER)


    def test_identify_compilation_server(self):
        self.util_test_identification_base(MockCompilationServerListener, Server.COMPILATION_SERVER)

    
    def test_identify_image_server(self):
        self.util_test_identification_base(MockImageServerListener, Server.APPLICATION_SERVER, Server.SUBTYPE_IMAGES)
    
    
    def test_identify_interactive_server(self):
        self.util_test_identification_base(MockInteractiveServerListener, Server.APPLICATION_SERVER, Server.SUBTYPE_INTERACTIVE)



class ServerIdentificatorTestCase(BaseTaskTest):

    def setUp(self):
        Server.objects.all().delete()
        Job.objects.all().delete()
        
        self.task = ServerIdentificator()
        self.task.start()

        # Avoid the startup phase
        self.util_wait_jobs_completion([self.task])

        Job.objects.all().delete()

        for i in range(0, 3):
            server             = Server()
            server.name        = 'Server%d' % (i + 1)
            server.address     = '127.0.0.1'
            server.port        = 18000 + i
            server.server_type = Server.UNIDENTIFIED_SERVER
            server.subtype     = Server.SUBTYPE_NONE
            server.status      = Server.SERVER_STATUS_UNKNOWN
            server.save()

        self.server1 = None


    def tearDown(self):
        del self.task

        if self.server1 is not None:
            self.server1.stop()

        Server.objects.all().delete()
        Job.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def test_no_server_online(self):
        self.assertEqual(0, Job.objects.count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())

        for server in Server.objects.all():
            self.assertTrue(self.task.processMessage(Message('IDENTIFY_SERVER', [server.id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(3, Job.objects.count())
        self.assertEqual(3, Job.objects.filter(status=Job.STATUS_DELAYED).count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())


    def util_test_identification_base(self, server_listener_class, server_type, server_subtype=None):
        self.assertEqual(0, Job.objects.count())
        self.assertEqual(3, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())

        self.server1 = ThreadedServer('127.0.0.1', 18000, server_listener_class)
        self.server1.start()
        time.sleep(1)

        self.assertTrue(self.task.processMessage(Message('IDENTIFY_SERVER', [Server.objects.get(port=18000).id])))

        self.util_wait_jobs_completion([self.task])

        self.assertEqual(1, Job.objects.count())
        self.assertEqual(1, Job.objects.filter(status=Job.STATUS_DONE).count())
        
        self.assertEqual(2, Server.objects.filter(server_type=Server.UNIDENTIFIED_SERVER).count())
        self.assertEqual(1, Server.objects.filter(server_type=server_type).count())

        server = Server.objects.filter(server_type=server_type)[0]

        self.assertEqual('Server1', server.name)

        if server_subtype is not None:
            self.assertEqual(server_subtype, server.subtype)


    def test_identify_experiments_server(self):
        self.util_test_identification_base(MockExperimentServerListener, Server.EXPERIMENTS_SERVER)


    def test_identify_compilation_server(self):
        self.util_test_identification_base(MockCompilationServerListener, Server.COMPILATION_SERVER)


    def test_identify_image_server(self):
        self.util_test_identification_base(MockImageServerListener, Server.APPLICATION_SERVER, Server.SUBTYPE_IMAGES)


    def test_identify_interactive_server(self):
        self.util_test_identification_base(MockInteractiveServerListener, Server.APPLICATION_SERVER, Server.SUBTYPE_INTERACTIVE)



def tests():
    return [ ServerIdentificatorStartupTestCase,
             ServerIdentificatorTestCase,
           ]

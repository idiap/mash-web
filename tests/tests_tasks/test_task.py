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
from tasks.task import Task
from pymash.messages import Message
from mash.servers.models import Job as ServerJob
from mocks.mock_task import MockTask
from mocks.mock_channelized_client import MockChannelizedClient
import shutil
import os


class TaskTestCase(unittest.TestCase):

    def setUp(self):
        ServerJob.objects.all().delete()
        
        self.clients = [
            MockChannelizedClient(),
            MockChannelizedClient(),
        ]

        self.task = MockTask()
        self.task.clients = self.clients
        self.task.start()


    def tearDown(self):
        del self.task
        del self.clients

        ServerJob.objects.all().delete()

        if os.path.exists('logs'):
            shutil.rmtree('logs')


    def test_onStartup(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)


    def test_onCommandReceived(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertTrue(self.task.processMessage('COMMAND1'))
        self.task.processNewJobs()

        m = self.task.out_channel.waitMessage()
        self.assertEqual('COMMAND1_DONE', m.name)


    def test_unknown_command(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage('COMMAND10'))


    def test_incorrect_number_of_arguments_for_command(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage(Message('COMMAND2', [4, 5])))


    def test_incorrect_type_of_arguments_for_command(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage(Message('COMMAND2', ['hello'])))


    def test_two_operations_command(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertTrue(self.task.processMessage(Message('COMMAND2',[10])))
        self.task.processNewJobs()

        m = self.clients[0].server_channel.waitMessage()
        self.assertEqual('NEXT', m.name)

        self.clients[0].server_channel.sendMessage('DATA')

        self.task.onEvent(None, [self.clients[0].client_channel.readPipe])

        m = self.task.out_channel.waitMessage()
        self.assertEqual('COMMAND2_DONE', m.name)


    def test_three_operations_command(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertTrue(self.task.processMessage(Message('COMMAND3',[10, 2.0, 'hello'])))
        self.task.processNewJobs()

        m = self.clients[1].server_channel.waitMessage()
        self.assertEqual('NEXT', m.name)

        self.clients[1].server_channel.sendMessage('DATA')

        self.task.onEvent(None, [self.clients[1].client_channel.readPipe])

        m = self.clients[1].server_channel.waitMessage()
        self.assertEqual('NEXT', m.name)

        self.clients[1].server_channel.sendMessage('DATA')

        self.task.onEvent(None, [self.clients[1].client_channel.readPipe])

        m = self.task.out_channel.waitMessage()
        self.assertEqual('COMMAND3_DONE', m.name)


    def test_onEventReceived(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertTrue(self.task.processMessage('EVENT1'))
        self.task.processNewJobs()

        m = self.task.out_channel.waitMessage()
        self.assertEqual('EVENT1_RECEIVED', m.name)


    def test_unknown_event(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage('EVENT10'))


    def test_incorrect_number_of_arguments_for_event(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage('EVENT2'))


    def test_incorrect_type_of_arguments_for_event(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertFalse(self.task.processMessage(Message('EVENT2', ['hello'])))


    def test_onEventCreatingAJobReceived(self):
        m = self.task.out_channel.waitMessage()
        self.assertEqual('STARTUP_DONE', m.name)

        self.assertTrue(self.task.processMessage(Message('EVENT3', [5])))
        self.task.processNewJobs()

        m = self.clients[0].server_channel.waitMessage()
        self.assertEqual('NEXT', m.name)

        self.clients[0].server_channel.sendMessage('DATA')

        self.task.onEvent(None, [self.clients[0].client_channel.readPipe])

        m = self.task.out_channel.waitMessage()
        self.assertEqual('COMMAND2_DONE', m.name)


def tests():
    return [ TaskTestCase ]

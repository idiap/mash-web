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
from pymash.messages import Message
from pymash.communication_channel import CommunicationChannel


class SimplexCommunicationChannelTestCase(unittest.TestCase):

    def setUp(self):
        (self.channel1, self.channel2) = CommunicationChannel.create(CommunicationChannel.CHANNEL_TYPE_SIMPLEX)

    def tearDown(self):
        self.channel1.close()
        self.channel2.close()

    def test_creation(self):
        self.assertTrue(self.channel1 is not None)
        self.assertTrue(self.channel2 is not None)
        self.assertTrue(self.channel1.writePipe is not None)
        self.assertTrue(self.channel1.readPipe is None)
        self.assertTrue(self.channel2.writePipe is None)
        self.assertTrue(self.channel2.readPipe is not None)
        self.assertTrue(self.channel1.lock is None)
        self.assertTrue(self.channel2.lock is None)

    def test_data_transmission(self):
        self.channel1.sendData('BLAH')
        data = self.channel2.readData(4)
        
        self.assertEqual('BLAH', data)

    def test_message_transmission(self):
        m1 = Message('SOME_NAME', [1, 2, 3])

        self.channel1.sendMessage(m1)
        m2 = self.channel2.waitMessage()

        self.assertTrue(m2.equals(m1))

    def test_string_message_transmission(self):
        m1 = Message('SOME_NAME', [1, 2, 3])

        self.channel1.sendMessage(m1.toString())
        m2 = self.channel2.waitMessage()

        self.assertTrue(m2.equals(m1))

    def test_multiple_messages_transmission(self):
        m1 = Message('SOME_NAME', [1, 2, 3])
        m2 = Message('ANOTHER_NAME', ['a', 'b', 'c'])

        self.channel1.sendMessage(m1)
        self.channel1.sendMessage(m2)
        
        m = self.channel2.waitMessage()
        self.assertTrue(m.equals(m1))

        m = self.channel2.waitMessage()
        self.assertTrue(m.equals(m2))

    def test_message_with_complicated_parameter_transmission(self):
        m1 = Message('SOME_NAME', ['This\nis a "complicated"\n\'parameter\''])

        self.channel1.sendMessage(m1)
        m2 = self.channel2.waitMessage()

        self.assertTrue(m2.equals(m1))

    def test_non_blocking_wait_for_message(self):
        m = self.channel2.waitMessage(block=False)

        self.assertTrue(m is None)


class FullDuplexCommunicationChannelTestCase(unittest.TestCase):

    def setUp(self):
        (self.channel1, self.channel2) = CommunicationChannel.create(CommunicationChannel.CHANNEL_TYPE_FULL_DUPLEX)

    def tearDown(self):
        self.channel1.close()
        self.channel2.close()

    def test_creation(self):
        self.assertTrue(self.channel1 is not None)
        self.assertTrue(self.channel2 is not None)
        self.assertTrue(self.channel1.writePipe is not None)
        self.assertTrue(self.channel1.readPipe is not None)
        self.assertTrue(self.channel2.writePipe is not None)
        self.assertTrue(self.channel2.readPipe is not None)
        self.assertTrue(self.channel1.lock is None)
        self.assertTrue(self.channel2.lock is None)

    def test_data_transmission_from_1_to_2(self):
        self.channel1.sendData('BLAH')
        data = self.channel2.readData(4)

        self.assertEqual('BLAH', data)

    def test_message_transmission_from_1_to_2(self):
        m1 = Message('SOME_NAME', [1, 2, 3])

        self.channel1.sendMessage(m1)
        m2 = self.channel2.waitMessage()

        self.assertTrue(m2.equals(m1))

    def test_data_transmission_from_2_to_1(self):
        self.channel2.sendData('BLAH')
        data = self.channel1.readData(4)

        self.assertEqual('BLAH', data)

    def test_message_transmission_from_2_to_1(self):
        m1 = Message('SOME_NAME', [1, 2, 3])

        self.channel2.sendMessage(m1)
        m2 = self.channel1.waitMessage()

        self.assertTrue(m2.equals(m1))


class MultiplexingCommunicationChannelTestCase(unittest.TestCase):

    def setUp(self):
        (self.channel1, self.channel2) = CommunicationChannel.create(CommunicationChannel.CHANNEL_TYPE_MULTIPLEXING)

    def tearDown(self):
        self.channel1.close()
        self.channel2.close()

    def test_creation(self):
        self.assertTrue(self.channel1 is not None)
        self.assertTrue(self.channel2 is not None)
        self.assertTrue(self.channel1.writePipe is not None)
        self.assertTrue(self.channel1.readPipe is None)
        self.assertTrue(self.channel2.writePipe is None)
        self.assertTrue(self.channel2.readPipe is not None)
        self.assertTrue(self.channel1.lock is not None)
        self.assertTrue(self.channel2.lock is None)

    def test_data_transmission(self):
        self.channel1.sendData('BLAH')
        data = self.channel2.readData(4)

        self.assertEqual('BLAH', data)

    def test_message_transmission(self):
        m1 = Message('SOME_NAME', [1, 2, 3])

        self.channel1.sendMessage(m1)
        m2 = self.channel2.waitMessage()

        self.assertTrue(m2.equals(m1))


def tests():
    return [ SimplexCommunicationChannelTestCase,
             FullDuplexCommunicationChannelTestCase,
             MultiplexingCommunicationChannelTestCase,
           ]

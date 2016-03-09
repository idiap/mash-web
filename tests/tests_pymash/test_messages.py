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


class MessageTestCase(unittest.TestCase):

    def test_name(self):
        m = Message('SOME_NAME')
        self.assertEqual('SOME_NAME', m.name)

    def test_no_parameters(self):
        m = Message('SOME_NAME')
        self.assertTrue(m.parameters is None)

    def test_empty_parameters(self):
        m = Message('SOME_NAME', [])
        self.assertTrue(m.parameters is None)

    def test_parameters(self):
        m = Message('SOME_NAME', [1, 2, 3])
        self.assertEqual([1, 2, 3], m.parameters)

    def test_equality(self):
        m1 = Message('SOME_NAME', [1, 2, 3])
        m2 = Message('SOME_NAME', [1, 2, 3])
        self.assertTrue(m1.equals(m2))
        self.assertTrue(m2.equals(m1))

    def test_inequality_in_name(self):
        m1 = Message('SOME_NAME1', [1, 2, 3])
        m2 = Message('SOME_NAME2', [1, 2, 3])
        self.assertFalse(m1.equals(m2))
        self.assertFalse(m2.equals(m1))

    def test_inequality_in_parameters(self):
        m1 = Message('SOME_NAME1', [1, 2, 3])
        m2 = Message('SOME_NAME2', [3, 2, 1])
        self.assertFalse(m1.equals(m2))
        self.assertFalse(m2.equals(m1))

    def test_to_string_without_parameter(self):
        m = Message('SOME_NAME')
        self.assertEqual('SOME_NAME', m.toString())

    def test_to_string_with_parameters(self):
        m = Message('SOME_NAME', [1, 2, 3])
        self.assertEqual('SOME_NAME 1 2 3', m.toString())

    def test_to_string_with_mixed_parameters(self):
        m = Message('SOME_NAME', [1, 2.0, 'hi', 'hello world'])
        self.assertEqual('SOME_NAME 1 2.0 hi \'hello world\'', m.toString())

    def test_to_string_with_complicated_parameters(self):
        m = Message('SOME_NAME', ['This\nis a "complicated"\n\'parameter\''])
        self.assertEqual('SOME_NAME \'This\\nis a "complicated"\\n\\\'parameter\\\'\'', m.toString())

    def test_from_string_without_parameter(self):
        m = Message('SOME_NAME')
        self.assertTrue(m.equals(Message.fromString('SOME_NAME')))

    def test_from_string_with_parameters(self):
        m = Message('SOME_NAME', [1, 2, 3])
        self.assertTrue(m.equals(Message.fromString('SOME_NAME 1 2 3')))

    def test_from_string_with_mixed_parameters(self):
        m = Message('SOME_NAME', [1, 2.0, 'hi', 'hello world'])
        self.assertTrue(m.equals(Message.fromString('SOME_NAME 1 2.0 hi \'hello world\'')))

    def test_from_string_with_complicated_parameters(self):
        m = Message('SOME_NAME', ['This\nis a "complicated"\n\'parameter\''])
        self.assertTrue(m.equals(Message.fromString('SOME_NAME \'This\\nis a "complicated"\\n\\\'parameter\\\'\'')))


def tests():
    return [ MessageTestCase ]

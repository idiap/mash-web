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
from django.conf import settings
from utilities.logs import saveLogFile
from utilities.logs import getServerLogs
from utilities.io import generateUniqueFolderName
from mash.logs.models import LogEntry
from mash.logs.models import LogFile
from mocks.mock_log_client import MockLogClient
import os
import shutil


class LogsTestCase(unittest.TestCase):

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        LogFile.objects.all().delete()
        LogEntry.objects.all().delete()

        fullpath = os.path.join(settings.LOG_FILES_ROOT, 'tests')
        if os.path.exists(fullpath):
            shutil.rmtree(fullpath)

    def test_saveLogFile(self):

        log_entry = LogEntry()
        log_entry.folder = 'tests'
        log_entry.save()

        fullpath = os.path.join(settings.LOG_FILES_ROOT, log_entry.folder)

        if not(os.path.exists(fullpath)):
            os.makedirs(fullpath)

        saveLogFile(log_entry, 'a.log', 'ABCDEF')
        saveLogFile(log_entry, 'b.log', 'GHIJKL')
        saveLogFile(log_entry, 'b.log', 'MNOPQR')
        saveLogFile(log_entry, 'b.log', 'STUVXY')

        self.assertEqual(4, log_entry.files.count())
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='a.log') is not None)
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='b.log') is not None)
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='b2.log') is not None)
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='b3.log') is not None)
        
        in_file = open(os.path.join(fullpath, 'a.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('ABCDEF', content)

        in_file = open(os.path.join(fullpath, 'b.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('GHIJKL', content)

        in_file = open(os.path.join(fullpath, 'b2.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('MNOPQR', content)

        in_file = open(os.path.join(fullpath, 'b3.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('STUVXY', content)

    def test_getServerLogs(self):

        client = MockLogClient()
        client.log_files.append( ('a.log', 'ABCDEF') )
        client.log_files.append( ('b.log', 'GHIJKL') )

        log_entry = getServerLogs(client)
        self.assertTrue(log_entry is not None)

        fullpath = os.path.join(settings.LOG_FILES_ROOT, log_entry.folder)

        self.assertEqual(2, log_entry.files.count())
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='a.log') is not None)
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='b.log') is not None)

        in_file = open(os.path.join(fullpath, 'a.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('ABCDEF', content)

        in_file = open(os.path.join(fullpath, 'b.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('GHIJKL', content)

        if os.path.exists(fullpath):
            shutil.rmtree(fullpath)

    def test_getFilteredServerLogs(self):

        client = MockLogClient()
        client.log_files.append( ('a.log', 'ABCDEF') )
        client.log_files.append( ('b.log', 'GHIJKL') )

        log_entry = getServerLogs(client, filter_list=['b.log'])
        self.assertTrue(log_entry is not None)

        fullpath = os.path.join(settings.LOG_FILES_ROOT, log_entry.folder)

        self.assertEqual(1, log_entry.files.count())
        self.assertTrue(log_entry.files.get(entry=log_entry.id, file='b.log') is not None)

        in_file = open(os.path.join(fullpath, 'b.log'))
        content = in_file.read()
        in_file.close()

        self.assertEqual('GHIJKL', content)

        if os.path.exists(fullpath):
            shutil.rmtree(fullpath)


def tests():
    return [ LogsTestCase ]

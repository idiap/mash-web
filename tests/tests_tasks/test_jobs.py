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
from tasks.jobs import Job
from tasks.jobs import JobList
from pymash.messages import Message
from mash.servers.models import Job as ServerJob
from mash.servers.models import Alert
from mash.servers.models import Server


class JobTestCase(unittest.TestCase):

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        ServerJob.objects.all().delete()
        Alert.objects.all().delete()
        Server.objects.all().delete()

    def util_createServer(self):
        server             = Server()
        server.name        = 'Test Server'
        server.address     = '127.0.0.1'
        server.port        = 10000
        server.server_type = Server.EXPERIMENTS_SERVER
        server.subtype     = Server.SUBTYPE_NONE
        server.status      = Server.SERVER_STATUS_ONLINE
        server.save()

        return server

    def test_creation_with_command(self):
        c = Message('SOME_NAME')
        job = Job(command=c)
        
        self.assertTrue(job.command.equals(c))
        self.assertTrue(job.server_job is not None)
        self.assertTrue(c.equals(Message.fromString(job.server_job.command)))
        self.assertEqual(job.server_job, ServerJob.objects.get(id=job.server_job.id))

    def test_creation_with_string_command(self):
        c = Message('SOME_NAME')
        job = Job(command=c.toString())

        self.assertTrue(job.command.equals(c))
        self.assertTrue(job.server_job is not None)
        self.assertTrue(c.equals(Message.fromString(job.server_job.command)))
        self.assertEqual(job.server_job, ServerJob.objects.get(id=job.server_job.id))

    def test_creation_with_command_and_parameters(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        self.assertTrue(job.command.equals(c))
        self.assertTrue(job.server_job is not None)
        self.assertTrue(c.equals(Message.fromString(job.server_job.command)))
        self.assertEqual(job.server_job, ServerJob.objects.get(id=job.server_job.id))

    def test_creation_with_string_command_and_parameters(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c.toString())

        self.assertTrue(job.command.equals(c))
        self.assertTrue(job.server_job is not None)
        self.assertTrue(c.equals(Message.fromString(job.server_job.command)))
        self.assertEqual(job.server_job, ServerJob.objects.get(id=job.server_job.id))

    def test_creation_with_server_job(self):
        c = Message('SOME_NAME', [1, 2, 3])

        server_job = ServerJob()
        server_job.command = c.toString()
        server_job.save()

        job = Job(server_job=server_job)

        self.assertTrue(job.command.equals(c))
        self.assertEqual(server_job, job.server_job)

    def test_mark_as_running(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        server = self.util_createServer()

        self.assertEqual(ServerJob.STATUS_SCHEDULED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)

        job.markAsRunning(server=server)

        self.assertEqual(ServerJob.STATUS_RUNNING, job.server_job.status)
        self.assertEqual(server, job.server_job.server)

    def test_mark_as_done(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        server = self.util_createServer()

        self.assertEqual(ServerJob.STATUS_SCHEDULED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)

        job.markAsRunning(server=server)
        job.markAsDone()

        self.assertEqual(ServerJob.STATUS_DONE, job.server_job.status)
        self.assertTrue(job.server_job.server is None)

    def test_mark_as_failed(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        server = self.util_createServer()

        alert = Alert()

        self.assertEqual(ServerJob.STATUS_SCHEDULED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)
        self.assertTrue(job.alert() is None)

        job.markAsRunning(server=server)
        job.markAsFailed(alert=alert)

        self.assertEqual(ServerJob.STATUS_FAILED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)
        self.assertEqual(alert, job.alert())
        self.assertEqual(alert, Alert.objects.get(id=alert.id))

    def test_mark_as_cancelled(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        server = self.util_createServer()

        self.assertEqual(ServerJob.STATUS_SCHEDULED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)
        self.assertTrue(job.alert() is None)

        job.markAsRunning(server=server)
        job.markAsCancelled()

        self.assertEqual(ServerJob.STATUS_CANCELLED, job.server_job.status)
        self.assertTrue(job.server_job.server is None)
        self.assertTrue(job.alert() is None)

    def test_mark_as_delayed(self):
        c = Message('SOME_NAME', [1, 2, 3])
        job = Job(command=c)

        self.assertEqual(ServerJob.STATUS_SCHEDULED, job.server_job.status)
        self.assertTrue(job.timeout is None)

        job.markAsDelayed(delay=10)

        self.assertEqual(ServerJob.STATUS_DELAYED, job.server_job.status)
        self.assertEqual(10, job.timeout)


class JobListTestCase(unittest.TestCase):

    def setUp(self):
        ServerJob.objects.all().delete()
        
        self.jobs = JobList()
        
        self.j1 = self.jobs.addJob(command='C1')
        
        self.j2 = self.jobs.addJob(command='C2')
        self.j2.markAsRunning()
        
        self.j3 = self.jobs.addJob(command='C3')
        
    def tearDown(self):
        self.j1 = None
        self.j2 = None
        self.j3 = None
        self.jobs = None
        
        ServerJob.objects.all().delete()

    def test_counts(self):
        self.assertEqual(3, self.jobs.count())
        self.assertEqual(2, self.jobs.count(ServerJob.STATUS_SCHEDULED))
        self.assertEqual(1, self.jobs.count(ServerJob.STATUS_RUNNING))
        self.assertEqual(0, self.jobs.count(ServerJob.STATUS_DONE))
        self.assertEqual(0, self.jobs.count(ServerJob.STATUS_FAILED))
        self.assertEqual(0, self.jobs.count(ServerJob.STATUS_DELAYED))

    def test_retrieve_scheduled_jobs(self):
        scheduled_jobs = self.jobs.getJobs(status=ServerJob.STATUS_SCHEDULED)

        self.assertEqual(2, len(scheduled_jobs))
        self.assertTrue(self.j1 in scheduled_jobs)
        self.assertFalse(self.j2 in scheduled_jobs)
        self.assertTrue(self.j3 in scheduled_jobs)

    def test_retrieve_jobs_by_command(self):
        jobs = self.jobs.getJobs(command='C2')

        self.assertEqual(1, len(jobs))
        self.assertFalse(self.j1 in jobs)
        self.assertTrue(self.j2 in jobs)
        self.assertFalse(self.j3 in jobs)

    def test_retrieve_scheduled_jobs_by_command(self):
        scheduled_jobs = self.jobs.getJobs(status=ServerJob.STATUS_SCHEDULED, command='C1')

        self.assertEqual(1, len(scheduled_jobs))
        self.assertTrue(self.j1 in scheduled_jobs)
        self.assertFalse(self.j2 in scheduled_jobs)
        self.assertFalse(self.j3 in scheduled_jobs)

    def test_has_job(self):
        self.assertTrue(self.jobs.hasJob('C1'))
        self.assertTrue(self.jobs.hasJob('C2'))
        self.assertTrue(self.jobs.hasJob('C3'))
        self.assertFalse(self.jobs.hasJob('C4'))

    def test_remove_jobs(self):
        scheduled_jobs = self.jobs.getJobs(ServerJob.STATUS_SCHEDULED)
        self.jobs.removeJobs(scheduled_jobs)

        self.assertEqual(1, self.jobs.count())
        self.assertEqual(0, self.jobs.count(ServerJob.STATUS_SCHEDULED))
        self.assertEqual(1, self.jobs.count(ServerJob.STATUS_RUNNING))

    def test_delayed_jobs(self):
        j1 = self.jobs.addJob(command='D1')
        j1.markAsDelayed(60)

        j2 = self.jobs.addJob(command='D2')
        j2.markAsDelayed(30)

        self.assertEqual(2, self.jobs.count(ServerJob.STATUS_SCHEDULED))
        self.assertEqual(2, self.jobs.count(ServerJob.STATUS_DELAYED))
        self.assertEqual(30, self.jobs.getNextTimeout())

        timeout_jobs = self.jobs.updateTimeouts(20)

        self.assertEqual(0, len(timeout_jobs))
        self.assertEqual(2, self.jobs.count(ServerJob.STATUS_DELAYED))
        self.assertEqual(10, self.jobs.getNextTimeout())

        timeout_jobs = self.jobs.updateTimeouts(20)

        self.assertEqual(1, len(timeout_jobs))
        self.assertEqual(1, self.jobs.count(ServerJob.STATUS_DELAYED))
        self.assertEqual(20, self.jobs.getNextTimeout())

        timeout_jobs = self.jobs.updateTimeouts(20)

        self.assertEqual(1, len(timeout_jobs))
        self.assertEqual(0, self.jobs.count(ServerJob.STATUS_DELAYED))
        self.assertTrue(self.jobs.getNextTimeout() is None)

        self.assertEqual(4, self.jobs.count(ServerJob.STATUS_SCHEDULED))


def tests():
    return [ JobTestCase, JobListTestCase ]

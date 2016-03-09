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
from mash.servers.models import Job
from pymash.messages import Message
from django.db.models import Q
import select


class BaseTaskTest(unittest.TestCase):

    def util_wait_jobs_completion(self, tasks):
        for task in filter(lambda x: len(x.new_jobs) > 0, tasks):
            task.processNewJobs()

        while Job.objects.filter(Q(status=Job.STATUS_SCHEDULED) | Q(status=Job.STATUS_RUNNING)).count() > 0:
            select_list = []
            for task in tasks:
                select_list.extend(self.task.getFileDescriptors())
            
            ready_to_read, ready_to_write, in_error = select.select(select_list, [], select_list)

            self.util_wait_jobs_completion_listener()

            for task in tasks:
                self.task.onEvent(None, ready_to_read)

    
    def util_wait_jobs_completion_listener(self):
        pass
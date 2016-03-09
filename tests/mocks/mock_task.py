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


from tasks.task import Task
from pymash.messages import Message


class MockTask(Task):

    SUPPORTED_COMMANDS = {
        'COMMAND1': [],
        'COMMAND2': [int],
        'COMMAND3': [int, float, str],
    }

    SUPPORTED_EVENTS = {
        'EVENT1': [],
        'EVENT2': [int],
        'EVENT3': [int],
    }
    
    
    def __init__(self):
        super(MockTask, self).__init__()
        
        self.clients = None

    
    def __del__(self):
        super(MockTask, self).__del__()
        del self.clients


    def process(self, job):
        # Should not happen
        if job.command.name == 'COMMAND1':
            self.channel.sendMessage('COMMAND1_ERROR')

        elif job.command.name == 'COMMAND2':
            job.markAsRunning()
            job.operation = MockTask.operation1
            job.client = self.clients[0]
            job.client.sendCommand('NEXT')

        elif job.command.name == 'COMMAND3':
            job.markAsRunning()
            job.operation = MockTask.operation1
            job.client = self.clients[1]
            job.client.sendCommand('NEXT')


    def operation1(self, job):
        r = job.client.waitResponse()
        
        if job.command.name == 'COMMAND2':
            job.markAsDone()
            job.client = None
            self.channel.sendMessage('COMMAND2_DONE')

        elif job.command.name == 'COMMAND3':
            job.operation = MockTask.operation2
            job.client.sendCommand('NEXT')


    def operation2(self, job):
        r = job.client.waitResponse()

        if job.command.name == 'COMMAND3':
            job.markAsDone()
            job.client = None
            self.channel.sendMessage('COMMAND3_DONE')


    def onStartup(self):
        self.channel.sendMessage('STARTUP_DONE')


    def onCommandReceived(self, command):
        if command.name == 'COMMAND1':
            self.channel.sendMessage('COMMAND1_DONE')
            return True

        return False


    def onEventReceived(self, event):
        if event.name == 'EVENT1':
            self.channel.sendMessage('EVENT1_RECEIVED')
        elif event.name == 'EVENT2':
            self.channel.sendMessage('EVENT2_RECEIVED')
        elif event.name == 'EVENT3':
            job = self.jobs.addJob(command=Message('COMMAND2', event.parameters))
            return [job]

        return None

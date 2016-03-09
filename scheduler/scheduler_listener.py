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


from pymash.server import ServerListener
from pymash.messages import Message


################################## CONSTANTS ###################################

PROTOCOL = '1.2'


########################### SCHEDULERLISTENER CLASS ############################

#-------------------------------------------------------------------------------
# The listener that will handle the incoming connections
#-------------------------------------------------------------------------------
class SchedulerListener(ServerListener):

    # Class attributes
    handlers = {
        'STATUS': 'handleStatusCommand',
        'INFO':   'handleInfoCommand',
        'DONE':   'handleDoneCommand',
    }
    
    
    OUTPUT_CHANNEL = None
    
    
    @classmethod
    def addCommand(cls, command_name, nb_parameters):
        cls.handlers[command_name] = ('handleOtherCommand', nb_parameters)


    #---------------------------------------------------------------------------
    # Called when a command was received
    #
    # @param command    The command
    # @return           The action to perform
    #---------------------------------------------------------------------------
    def handleCommand(self, command):
        try:
            if isinstance(SchedulerListener.handlers[command.name], tuple):
                # Check the number of arguments
                if command.parameters is None:
                    if SchedulerListener.handlers[command.name][1] > 0:
                        if not(self.sendResponse('INVALID_ARGUMENT')):
                            return ServerListener.ACTION_CLOSE_CONNECTION
                        return ServerListener.ACTION_NONE
                else:
                    if SchedulerListener.handlers[command.name][1] == 0:
                        if not(self.sendResponse('INVALID_ARGUMENT')):
                            return ServerListener.ACTION_CLOSE_CONNECTION
                        return ServerListener.ACTION_NONE

                    if len(command.parameters) != SchedulerListener.handlers[command.name][1]:
                        if not(self.sendResponse('INVALID_ARGUMENT')):
                            return ServerListener.ACTION_CLOSE_CONNECTION
                        return ServerListener.ACTION_NONE

                method = self.__getattribute__(SchedulerListener.handlers[command.name][0])
                return method(command)
            else:
                method = self.__getattribute__(SchedulerListener.handlers[command.name])
                return method(command.parameters)
        except:
            if not(self.sendResponse(Message('UNKNOWN_COMMAND', [command.name]))):
                return ServerListener.ACTION_CLOSE_CONNECTION
            
            return ServerListener.ACTION_NONE


    #---------------------------------------------------------------------------
    # Called when a 'STATUS' command was received
    #
    # @param arguments  Arguments of the command
    # @return           The action to perform
    #---------------------------------------------------------------------------
    def handleStatusCommand(self, arguments):
        if not(self.sendResponse('READY')):
            return ServerListener.ACTION_CLOSE_CONNECTION
            
        return ServerListener.ACTION_NONE


    #---------------------------------------------------------------------------
    # Called when a 'INFO' command was received
    #
    # @param arguments  Arguments of the command
    # @return           The action to perform
    #---------------------------------------------------------------------------
    def handleInfoCommand(self, arguments):
        if not(self.sendResponse(Message('TYPE', ['Scheduler'])) and \
               self.sendResponse(Message('PROTOCOL', [PROTOCOL]))):
            return ServerListener.ACTION_CLOSE_CONNECTION

        return ServerListener.ACTION_NONE


    #---------------------------------------------------------------------------
    # Called when a 'DONE' command was received
    #
    # @param arguments  Arguments of the command
    # @return           The action to perform
    #---------------------------------------------------------------------------
    def handleDoneCommand(self, arguments):
        self.sendResponse('GOODBYE')
        return ServerListener.ACTION_CLOSE_CONNECTION


    #---------------------------------------------------------------------------
    # Called when a command that must be handled by the scheduler class was
    # received
    #
    # @param arguments  Arguments of the command
    # @return           The action to perform
    #---------------------------------------------------------------------------
    def handleOtherCommand(self, command):        
        SchedulerListener.OUTPUT_CHANNEL.sendMessage(command)
        if not(self.sendResponse('OK')):
            return ServerListener.ACTION_CLOSE_CONNECTION

        return ServerListener.ACTION_NONE

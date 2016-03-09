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


from pymash.communication_channel import CommunicationChannel


class MockChannelizedClient(object):
    
    def __init__(self):
        (self.client_channel, self.server_channel) = CommunicationChannel.create(
                                                            CommunicationChannel.CHANNEL_TYPE_FULL_DUPLEX)
        
        self.socket = self.client_channel.readPipe
    
    def __del__(self):
        self.close()
    
    def sendCommand(self, command):
        self.client_channel.sendMessage(command)
        return True
    
    def waitResponse(self):
        return self.client_channel.waitMessage()

    def hasResponse(self):
        return (self.client_channel.read_buffer.find('\n') != -1)

    def close(self):
        del self.client_channel
        del self.server_channel
        self.client_channel = None
        self.server_channel = None
        
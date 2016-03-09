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


from pymash.messages import Message


class MockLogClient(object):
    
    def __init__(self):
        self.log_files = []
        self.current = 0
    
    def sendCommand(self, command):
        self.current = 0
        return (command == 'LOGS')
    
    def waitResponse(self):
        if self.current >= len(self.log_files):
            return Message('END_LOGS')
        
        name = self.log_files[self.current][0]
        size = len(self.log_files[self.current][1])
        
        return Message('LOG_FILE', [name, size])
    
    def waitData(self, size):
        if self.current >= len(self.log_files):
            return None
        
        if size != len(self.log_files[self.current][1]):
            return None

        data = self.log_files[self.current][1]
        
        self.current += 1
        
        return data

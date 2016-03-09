#! /usr/bin/env python

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
from threading import Lock
import os
import select


#-------------------------------------------------------------------------------
# Represents one end-point of a communication channel between two processes or
# threads
#
# Use the CommunicationChannel.create() static method to create two connected
# end-points correctly configured.
#-------------------------------------------------------------------------------
class CommunicationChannel:

    # Constants
    CHANNEL_TYPE_SIMPLEX      = 0
    CHANNEL_TYPE_FULL_DUPLEX  = 1
    CHANNEL_TYPE_MULTIPLEXING = 2


    #---------------------------------------------------------------------------
    # Create two connected end-points configured for the provided channel type
    #
    # Returns the pair of end-points as (channel1, channel2). For all channel
    # types, 'channel1' can send messages to 'channel2'.
    #---------------------------------------------------------------------------
    @staticmethod
    def create(channel_type):
        if channel_type == CommunicationChannel.CHANNEL_TYPE_SIMPLEX:
            (r, w) = os.pipe()
            return (CommunicationChannel(w=w), CommunicationChannel(r=r))

        elif channel_type == CommunicationChannel.CHANNEL_TYPE_FULL_DUPLEX:
            (r1, w1) = os.pipe()
            (r2, w2) = os.pipe()
            return (CommunicationChannel(w=w1, r=r2), CommunicationChannel(w=w2, r=r1))

        elif channel_type == CommunicationChannel.CHANNEL_TYPE_MULTIPLEXING:
            (r, w) = os.pipe()
            return (CommunicationChannel(w=w, multiplexing=True), CommunicationChannel(r=r))

        else:
            return (None, None)


    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self, w=None, r=None, multiplexing=False):
        self.writePipe = w
        self.readPipe = r
        self.read_buffer = ''
        self.lock = None

        if multiplexing and (w is not None):
            self.lock = Lock()


    #---------------------------------------------------------------------------
    # Destructor
    #---------------------------------------------------------------------------
    def __del__(self):
        self.close()


    #---------------------------------------------------------------------------
    # Close the communication channel
    #---------------------------------------------------------------------------
    def close(self):
        if self.writePipe is not None:
            os.close(self.writePipe)
            self.writePipe = None

        if self.readPipe is not None:
            os.close(self.readPipe)
            self.readPipe = None


    #---------------------------------------------------------------------------
    # Send a message
    #
    # @param  message   The message
    #---------------------------------------------------------------------------
    def sendMessage(self, message):
        if self.writePipe is None:
            return

        if isinstance(message, Message):
            message = message.toString()

        self.sendData(message + '\n')


    #---------------------------------------------------------------------------
    # Send a buffer of data
    #
    # @param  data   The data
    #---------------------------------------------------------------------------
    def sendData(self, data):
        if self.writePipe is None:
            return

        if self.lock is not None:
            self.lock.acquire()

        try:
            os.write(self.writePipe, data)
        except:
            pass
        finally:
            if self.lock is not None:
                self.lock.release()


    #---------------------------------------------------------------------------
    # Retrieve the next message (can be a blocking or a non-blocking call)
    #---------------------------------------------------------------------------
    def waitMessage(self, block=True):
        if self.readPipe is None:
            return None

        # Process the data already in the buffer
        message = self._extractMessageFromBuffer()
        if message is not None:
            return Message.fromString(message)

        MAXDATASIZE = 256
        eof = False

        while not(eof):
            # Determine if some data was received
            select_list = [self.readPipe]

            if block:
                timeout = None
            else:
                timeout = 0

            ready_to_read, ready_to_write, in_error = select.select(select_list, [], select_list, timeout)

            if (self.readPipe in ready_to_read):
                data = self.readData(MAXDATASIZE)
                if (data is None) or (len(data) <= 0):
                    break

                self.read_buffer += data
            else:
                eof = True

            # Process the data in the buffer
            message = self._extractMessageFromBuffer()
            if message is not None:
                return Message.fromString(message)

        return None


    #---------------------------------------------------------------------------
    # Receives a buffer of data
    #
    # @param    count   The number of bytes to read
    # @return           The data
    #---------------------------------------------------------------------------
    def readData(self, count):
        if self.readPipe is None:
            return None

        data = None

        try:
            data = os.read(self.readPipe, count)
        finally:
            pass

        return data


    #---------------------------------------------------------------------------
    # Retrieves the next message in the internal buffer of received data
    #---------------------------------------------------------------------------
    def _extractMessageFromBuffer(self):

        offset = self.read_buffer.find('\n')
        while offset != -1:
            line = self.read_buffer[0:offset]
            self.read_buffer = self.read_buffer[offset+1:];

            if offset == 0:
                offset = self.read_buffer.find('\n')
                continue

            return line

        return None

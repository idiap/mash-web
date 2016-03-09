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


from pymash.networkutils import NetworkUtils
from pymash.messages import Message
from pymash.outstream import OutStream
import socket
import traceback


#-------------------------------------------------------------------------------
# Represents a client, connected to a server through a network connection
#-------------------------------------------------------------------------------
class Client:

    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self, outStream=None):
        self.socket = None
        self.buffer = ''
        self.outStream = outStream


    #---------------------------------------------------------------------------
    # Establish a connection with a server
    #---------------------------------------------------------------------------
    def connect(self, address, port):
        if self.socket:
            self.close()

        if self.outStream is not None:
            self.outStream.write("Trying to establish a connection to '%s:%d'\n" % (address, port))

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((address, port))
        except socket.error:
            self.close()
            if self.outStream is not None:
                self.outStream.write("ERROR - Failed to establish a connection with the server\n")
            return False

        if self.outStream is not None:
            self.outStream.write("Connection established with the server\n")

        return True


    #---------------------------------------------------------------------------
    # Close the connection
    #---------------------------------------------------------------------------
    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
            self.buffer = ''


    #---------------------------------------------------------------------------
    # Send a command to the server
    #
    # @param  command   The command
    #---------------------------------------------------------------------------
    def sendCommand(self, command):
        if self.socket is None:
            return False

        if not(isinstance(command, Message)):
            command = Message.fromString(command)

        if self.outStream is not None:
            self.outStream.write("> %s\n" % command.toString())

        try:
            result = NetworkUtils.sendMessage(self.socket, command)
        except socket.error:
            result = None
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to send the command, reason: %s\n" % traceback.format_exc())

        return result


    #---------------------------------------------------------------------------
    # Send some data to the server
    #
    # @param  data   The data
    #---------------------------------------------------------------------------
    def sendData(self, data):
        if self.socket is None:
            return False

        if self.outStream is not None:
            self.outStream.write("> <%d bytes of data>\n" % len(data))

        try:
            result = NetworkUtils.sendData(self.socket, data)
        except socket.error:
            result = False
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to send the data, reason: %s\n" % traceback.format_exc())

        return result


    #---------------------------------------------------------------------------
    # Retrieve the next response from the server (blocking call)
    #---------------------------------------------------------------------------
    def waitResponse(self):
        try:
            (response, self.buffer) = NetworkUtils.waitMessage(self.socket, self.buffer)
        except socket.error:
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for a response, reason: %s\n" % traceback.format_exc())
            return None

        if response is None:
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for a response\n")
            return None

        if self.outStream is not None:
            self.outStream.write("< %s\n" % response.toString())

        return response


    #---------------------------------------------------------------------------
    # Retrieve the some data from the server (blocking call)
    #---------------------------------------------------------------------------
    def waitData(self, size):
        try:
            (data, self.buffer) = NetworkUtils.waitData(self.socket, self.buffer, size)
        except socket.error:
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for %d bytes of data, reason: %s\n" % (size, traceback.format_exc()))
            return None

        if data is None:
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for %d bytes of data\n" % size)
            return None

        if self.outStream is not None:
            self.outStream.write("< <%d bytes of data>\n" % size)

        return data


    #---------------------------------------------------------------------------
    # Indicates if the next response from the server is already in the internal
    # buffer
    #---------------------------------------------------------------------------
    def hasResponse(self):
        return (self.buffer.find('\n') != -1)

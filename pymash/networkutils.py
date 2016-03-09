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
import select
import socket


#-------------------------------------------------------------------------------
# Utility class to send and receive messages and data using a network connection
#-------------------------------------------------------------------------------
class NetworkUtils:

    #---------------------------------------------------------------------------
    # Send a message
    #
    # @param  message   The message
    #---------------------------------------------------------------------------
    @staticmethod
    def sendMessage(thesocket, message):
        if isinstance(message, Message):
            message = message.toString()

        message += '\n'

        # Send the message
        try:
            while len(message) > 0:
                nb = thesocket.send(message)
                message = message[nb:]
        except socket.error:
            raise

        return True


    #---------------------------------------------------------------------------
    # Send a buffer of data
    #
    # @param  data   The data
    #---------------------------------------------------------------------------
    @staticmethod
    def sendData(thesocket, data):

        # Send the data
        try:
            while len(data) > 0:
                nb = thesocket.send(data)
                data = data[nb:]
        except socket.error:
            raise

        return True


    #---------------------------------------------------------------------------
    # Retrieve the next message (can be a blocking or a non-blocking call)
    #
    # An optional 'interrupt channel' can be provided. If some data can be read
    # using it, the wait is over.
    #---------------------------------------------------------------------------
    @staticmethod
    def waitMessage(thesocket, buffer, interrupt_channel=None, block=True):

        MAXDATASIZE = 256

        try:
            (message, buffer) = NetworkUtils._extractMessageFromBuffer(buffer)
            if message is not None:
                return (Message.fromString(message), buffer)

            select_list = [thesocket]
            if interrupt_channel is not None:
                select_list.append(interrupt_channel.readPipe)

            if block:
                timeout = None
            else:
                timeout = 0

            while True:
                ready_to_read, ready_to_write, in_error = select.select(select_list, [], select_list)

                if thesocket in ready_to_read:
                    data = thesocket.recv(MAXDATASIZE)
                    if len(data) <= 0:
                        break

                    buffer += data

                    (message, buffer) = NetworkUtils._extractMessageFromBuffer(buffer)
                    if message is not None:
                        return (Message.fromString(message), buffer)

                elif (interrupt_channel is not None) and (interrupt_channel.readPipe in ready_to_read):
                    break

                elif (thesocket in in_error):
                    print "ERROR IN SOCKET"

        except socket.error:
            raise

        return (None, buffer)


    #---------------------------------------------------------------------------
    # Retrieve some data (blocking call)
    #
    # An optional 'interrupt channel' can be provided. If some data can be read
    # using it, the wait is over.
    #---------------------------------------------------------------------------
    @staticmethod
    def waitData(thesocket, buffer, size, interrupt_channel=None):

        total = 0
        bytesleft = size
        data = ''

        try:
            if len(buffer) >= size:
                return (buffer[0:size], buffer[size:])

            elif len(buffer) > 0:
                data = buffer
                total = len(buffer)
                bytesleft -= total;
                buffer = ''

            select_list = [thesocket]
            if interrupt_channel is not None:
                select_list.append(interrupt_channel.readPipe)

            while True:
                ready_to_read, ready_to_write, in_error = select.select(select_list, [], select_list)

                if thesocket in ready_to_read:
                    received_data = thesocket.recv(bytesleft)

                    if len(received_data) <= 0:
                        break

                    data += received_data
                    total += len(received_data)
                    bytesleft -= len(received_data)

                    if bytesleft == 0:
                        return (data, buffer)

                elif (interrupt_channel is not None) and (interrupt_channel.readPipe in ready_to_read):
                    break

        except socket.error:
            raise

        return (data, buffer)


    #---------------------------------------------------------------------------
    # Retrieves the next message in the provided buffer of data
    #---------------------------------------------------------------------------
    @staticmethod
    def _extractMessageFromBuffer(buffer):

        offset = buffer.find('\n')
        while offset != -1:
            line = buffer[0:offset]
            buffer = buffer[offset+1:];

            if offset == 0:
                offset = buffer.find('\n')
                continue

            return (line, buffer)

        return (None, buffer)

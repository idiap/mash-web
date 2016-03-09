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
from pymash.communication_channel import CommunicationChannel
from pymash.outstream import OutStream
from pymash.messages import Message
from threading import Thread
import socket
import os
import sys
import signal
import select
import datetime
import traceback


def term_signal_handler(signum, frame):
    raise KeyboardInterrupt


#-------------------------------------------------------------------------------
# Represents a server listener, which handle the requests sent by a client
#
# The application must provide a class inheriting this one, and implementing
# the 'handleCommand()' method.
#-------------------------------------------------------------------------------
class ServerListener(Thread):

    # Constants
    ACTION_NONE             = 0     # No specific action
    ACTION_CLOSE_CONNECTION = 1     # Close the connection with the client
    ACTION_SLEEP            = 2     # The server must go to sleep


    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self, socket, channel):
        Thread.__init__(self)
        self.deamon     = True
        self.socket     = socket
        self.channel    = channel
        self.outStream  = OutStream()
        self.buffer     = ''
        self.identifier = socket.fileno()


    #---------------------------------------------------------------------------
    # Called when the thread is started
    #---------------------------------------------------------------------------
    def run(self):
        while (True):
            try:
                (command, self.buffer) = NetworkUtils.waitMessage(self.socket, self.buffer, self.channel)
            except socket.error:
                command = None
                if self.outStream is not None:
                    self.outStream.write("ERROR: Failed to wait for a response, reason: %s\n" % traceback.format_exc())
                break
            except select.error:
                command = None
                if self.outStream is not None:
                    self.outStream.write("The server is shutting down...\n")
                break

            if command is None:
                break

            self.outStream.write("< %s\n" % command.toString())

            action = self.handleCommand(command)

            if action == ServerListener.ACTION_SLEEP:
                self.channel.sendMessage(Message('SLEEP', [self.identifier]))
            elif action != ServerListener.ACTION_NONE:
                break

        self.socket.close()
        self.outStream.delete()

        self.channel.sendMessage(Message('DONE', [self.identifier]))


    def stop(self):
        try:
            self.socket.close()
            return True
        except:
            return False


    #---------------------------------------------------------------------------
    # Wait for data from the client
    #---------------------------------------------------------------------------
    def waitData(self, size):
        try:
            (data, self.buffer) = NetworkUtils.waitData(self.socket, self.buffer, size)
        except socket.error:
            data = None
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for %d bytes of data, reason: %s\n" % (size, traceback.format_exc()))

        if data is None:
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to wait for %d bytes of data\n" % size)
            return None

        if self.outStream is not None:
            self.outStream.write("< <%d bytes of data>\n" % size)

        return data


    #---------------------------------------------------------------------------
    # Send a response to the client
    #---------------------------------------------------------------------------
    def sendResponse(self, response):
        if not(isinstance(response, Message)):
            response = Message.fromString(response)

        self.outStream.write("> %s\n" % response.toString())

        try:
            result = NetworkUtils.sendMessage(self.socket, response)
        except socket.error:
            result = False
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to send the response, reason: %s\n" % traceback.format_exc())

        return result


    #---------------------------------------------------------------------------
    # Send some data to the client
    #---------------------------------------------------------------------------
    def sendData(self, data):
        self.outStream.write("> <%d bytes of data>\n" % len(data))

        try:
            result = NetworkUtils.sendData(self.socket, data)
        except socket.error:
            result = False
            if self.outStream is not None:
                self.outStream.write("ERROR: Failed to send the data, reason: %s\n" % traceback.format_exc())

        return result


    #---------------------------------------------------------------------------
    # Method to be implemented by the listener class, to handle a command sent
    # by the client
    #---------------------------------------------------------------------------
    def handleCommand(self, command):
        return ServerListener.ACTION_NONE



#-------------------------------------------------------------------------------
# The server listener used by the server to handle commands when the server is
# busy
#-------------------------------------------------------------------------------
class BusyListener(ServerListener):

    def __init__(self, socket, channel, listenerClass):
        super(BusyListener, self).__init__(socket, channel)
        self.listenerClass = listenerClass

    def handleCommand(self, command):
        if command.name == 'INFO':
            listener = self.listenerClass(self.socket)
            return listener.handleCommand(command)
        elif command.name == 'DONE':
            self.sendResponse('GOODBYE')
            return ServerListener.ACTION_CLOSE_CONNECTION
        elif command.name == 'SLEEP':
            self.sendResponse('OK')
            return ServerListener.ACTION_SLEEP
        else:
            self.sendResponse('BUSY')
            return ServerListener.ACTION_CLOSE_CONNECTION


#-------------------------------------------------------------------------------
# Represents a server
#
# A server waits for incoming connections, and create either one thread to
# handle the requests from the client.
#
# The server can either be used as the main loop of the application (managing
# everything itself), or integrated in another loop (the application must call
# the methods of the server at appropriate time)
#-------------------------------------------------------------------------------
class Server:

    # Constants
    STATE_NORMAL            = 0
    STATE_GOING_TO_SLEEP    = 1
    STATE_SLEEPING          = 2


    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__(self, nbMaxClients=0, name='Server', logLimit=100, logFolder='logs'):
        self.nbMaxClients   = nbMaxClients
        self.state          = Server.STATE_NORMAL
        self.logLimit       = logLimit
        self.controlPipe    = None
        self.host           = None
        self.port           = None
        self.serversocket   = None
        self.listeners      = []
        self.clientsCounter = 0

        (self.listener_channel, self.server_channel) = \
                CommunicationChannel.create(CommunicationChannel.CHANNEL_TYPE_FULL_DUPLEX)

        self.outStream = OutStream()
        self.outStream.open(name, os.path.join(logFolder, '%s-$TIMESTAMP.log' % name))


    #---------------------------------------------------------------------------
    # Listen for incoming connections and handle them (blocking call)
    #---------------------------------------------------------------------------
    def run(self, host, port, listenerClass):

        if not (self.listen(host, port)):
            return False

        # Install the TERM signal handler
        try:
            signal.signal(signal.SIGTERM, term_signal_handler)
        except ValueError:
            # Happens when not in the main thread
            pass

        self.controlPipe = os.pipe()

        try:
            while True:
                # Wait for some events
                self.outStream.write("--------------------------------------------------------------------------------\n")
                self.outStream.write("Waiting...\n")

                descriptors = self.fileDescriptors()
                ready_to_read, ready_to_write, in_error = select.select(descriptors, [], descriptors)

                if not(self.processEvents(ready_to_read, listenerClass)):
                    break

        except KeyboardInterrupt:
            self.serversocket.close()
            self.terminateListeners()
            os.close(self.controlPipe[0])
            os.close(self.controlPipe[1])
            raise

        self.serversocket.close()
        self.terminateListeners()

        os.close(self.controlPipe[0])
        os.close(self.controlPipe[1])

        return True


    #---------------------------------------------------------------------------
    # Stop the server (only if the 'run()' method is used)
    #---------------------------------------------------------------------------
    def stop(self):
        if self.controlPipe is not None:
            os.write(self.controlPipe[1], "DONE")


    #---------------------------------------------------------------------------
    # Setup the listening for incoming connections
    #---------------------------------------------------------------------------
    def listen(self, host, port):
        self.host = host
        self.port = port

        if len(host) > 0:
            self.outStream.write("Start to listen for incoming connections on '%s:%d'\n" % (host, port))
        else:
            self.outStream.write("Start to listen for incoming connections on port %d\n" % port)

        if self.nbMaxClients > 0:
            self.outStream.write("This server only supports %d client(s) at the same time\n" % self.nbMaxClients)
        else:
            self.outStream.write("This server supports an unlimited amount of clients\n")

        try:
            # Create and bind the server socket
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.serversocket.bind((host, port))

            # Start listening
            self.serversocket.listen(max(self.nbMaxClients * 2, 10))
        except socket.error:
            self.outStream.write("ERROR - Failed to listen for incoming connections\n")
            return False

        return True


    #---------------------------------------------------------------------------
    # Returns the list of file descriptors that the server wants to read
    #---------------------------------------------------------------------------
    def fileDescriptors(self):
        descriptors = [self.serversocket, self.server_channel.readPipe]

        if self.controlPipe is not None:
            descriptors.append(self.controlPipe[0])

        return descriptors


    #---------------------------------------------------------------------------
    # Process the events that happened on our file descriptors
    #---------------------------------------------------------------------------
    def processEvents(self, ready_to_read_descriptors, listenerClass):

        # Process the events coming from the listeners
        done_listeners = []
        while True:
            message = self.server_channel.waitMessage(block=False)
            if message is None:
                break

            if message.name == 'SLEEP':
                self.outStream.write("Going to sleep...\n")
                self.state = Server.STATE_GOING_TO_SLEEP

            done_listeners.append(message.parameters[0])

        nbListeners = len(self.listeners)
        self.listeners = filter(lambda x: x.identifier not in done_listeners, self.listeners)

        if len(self.listeners) != nbListeners:
            diff = nbListeners - len(self.listeners)
            if diff > 1:
                self.outStream.write("%d clients are done\n" % diff)
            else:
                self.outStream.write("One client is done\n")


        if (self.state == Server.STATE_GOING_TO_SLEEP) and (len(self.listeners) == 0):
            self.outStream.write("Sleeping...\n")
            self.state = Server.STATE_SLEEPING


        # Process commands
        if (self.controlPipe is not None) and (self.controlPipe[0] in ready_to_read_descriptors):
            return False


        # Process the incoming connections
        if self.serversocket in ready_to_read_descriptors:
            try:
                (clientsocket, address) = self.serversocket.accept()

                self.outStream.write("Incoming connection from %s\n" % str(address))

                # Determine if we can handle this client
                busy = False
                if self.state == Server.STATE_SLEEPING:
                    busy = True
                    self.outStream.write("The server is sleeping, there is currently %d clients connected\n" % len(self.listeners));
                elif self.state == Server.STATE_GOING_TO_SLEEP:
                    busy = True
                    self.outStream.write("The server is going to sleep, there is still %d clients connected\n" % len(self.listeners));
                elif self.nbMaxClients > 0:
                    busy = (len(self.listeners) >= self.nbMaxClients)
                    if busy:
                        self.outStream.write("The server is busy (%d/%d client(s) connected)\n" % (len(self.listeners), self.nbMaxClients))
                    else:
                        self.outStream.write("The server is available (%d/%d client(s) connected)\n" % (len(self.listeners), self.nbMaxClients))
                else:
                    self.outStream.write("The server is available (%d client(s) connected)\n" % len(self.listeners))

                # Create a new thread to handle the connection
                if (self.state == Server.STATE_NORMAL) and not(busy):
                    listener = listenerClass(clientsocket, self.listener_channel)
                else:
                    listener = BusyListener(clientsocket, self.listener_channel, listenerClass)

                listener.start()
                self.listeners.append(listener)

                self.clientsCounter += 1
            except socket.error:
                self.outStream.write("Failed to accept a connection, reason: %s\n" % traceback.format_exc())


        # Delete the log file and starts a new one when the limit is reached
        if (self.clientsCounter >= self.logLimit) and (len(self.listeners) == 0):
            self.outStream.write("--------------------------------------------------------------------------------\n")

            logName = self.outStream.name
            logFileName = self.outStream.filename
            self.outStream.delete()
            self.outStream.open(logName, logFileName)

            self.outStream.write("Reset of the log file: %s\n" % datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

            if len(self.host) > 0:
                self.outStream.write("Listen for incoming connections on '%s:%d'\n" % (self.host, self.port))
            else:
                self.outStream.write("Listen for incoming connections on port %d\n" % self.port)

            if self.nbMaxClients > 0:
                self.outStream.write("This server only supports %d client(s) at the same time\n" % self.nbMaxClients)
            else:
                self.outStream.write("This server supports an unlimited amount of clients\n")

            self.clientsCounter = 0

        return True


    def terminateListeners(self):
        for listener in self.listeners:
            if listener.stop():
                listener.join()

        self.listeners = []


#-------------------------------------------------------------------------------
# A thread that manage a server instance
#-------------------------------------------------------------------------------
class ThreadedServer(Thread):

    def __init__ (self, hostname, port, listenerClass, nbMaxClients=0,
                  name='Server', logLimit=100, logFolder='logs'):
       Thread.__init__(self)
       self.deamon = True
       self.hostname = hostname
       self.port = port
       self.listenerClass = listenerClass
       self.server = Server(nbMaxClients=nbMaxClients, name=name,
                            logLimit=logLimit, logFolder=logFolder)

    def run(self):
        self.server.run(self.hostname, self.port, self.listenerClass)

    def stop(self):
        self.server.stop()

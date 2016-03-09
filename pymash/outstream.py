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


from threading import Lock
import datetime
import os
import sys




class OutStream:

    outputToConsole = False
    lock            = Lock()


    def __init__(self):
        self.name       = ''
        self.filename   = None
        self.file       = None
        self.newLine    = True

    def __del__(self):
        self.close()

    def open(self, name, filename):
        if self.file is not None:
            self.close()

        # Initialisations
        self.name = name
        self.newline = True

        self.filename = filename.replace('$TIMESTAMP', datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

        # Create the folders if necessary
        dirname = os.path.dirname(self.filename)
        try:
            if not(os.path.exists(dirname)):
                os.makedirs(dirname)
        except:
            pass

        # Open the file
        self.file = open(self.filename, 'w')
        if self.file is not None:
            self.file.write("""********************************************************************************
*
*                   %s
*
********************************************************************************

""" % name)
            self.file.flush()

        return (self.file is not None)

    def close(self):

        OutStream.lock.acquire()

        try:

            if self.file is not None:
                self.file.write("---------------- End of the log file ----------------\n")
                self.file.close()
                self.file = None

        finally:
            OutStream.lock.release()


    def delete(self):
        self.close()

        if self.filename is not None:
            if os.path.exists(self.filename):
                os.remove(self.filename)
            self.filename = None

    def write(self, text, timestamp=False):

        OutStream.lock.acquire()

        try:
            if timestamp:
                text = "(%s) %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text)

            if self.file is not None:
                self.file.write(text)
                self.file.flush()

            if OutStream.outputToConsole:
                if self.newLine:
                    sys.stdout.write('{%s} %s' % (self.name, text))
                else:
                    sys.stdout.write('%s' % text)

                sys.stdout.flush()

                self.newLine = False

                if (len(text) > 0) and (text[-1] == '\n'):
                    self.newLine = True

        finally:
            OutStream.lock.release()



    def dump(self, max_size=None):
        if self.file is None:
            return None

        file2 = open(self.filename, 'r')

        file2.seek(0, os.SEEK_END)
        size = file2.tell()

        if (max_size > 0) and (max_size < 100):
            max_size = 100

        if (max_size > 0) and (size > max_size):
            file2.seek(-max_size + 4, os.SEEK_END)
        else:
            file2.seek(0, os.SEEK_SET)

        content = file2.read()
        file2.close()

        if (max_size > 0) and (size > max_size):
            content = '...\n' + content

        return content

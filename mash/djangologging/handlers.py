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


from logging import Handler


try:
    import threading
    threading_supported = True
except ImportError:
    threading_supported = False


class ThreadBufferedHandler(Handler):
    """ A logging handler that buffers records by thread. """
    
    def __init__(self):
        if not threading_supported:
            raise NotImplementedError("ThreadBufferedHandler cannot be used "
                "if threading is not supported.")
        Handler.__init__(self)
        self.records = {} # Dictionary (Thread -> list of records)

    def emit(self, record):
        """ Append the record to the buffer for the current thread. """
        self.get_records().append(record)

    def get_records(self, thread=None):
        """
        Gets the log messages of the specified thread, or the current thread if
        no thread is specified.
        """
        if not thread:
            thread = threading.currentThread()
        if thread not in self.records:
            self.records[thread] = []
        return self.records[thread]

    def clear_records(self, thread=None):
        """
        Clears the log messages of the specified thread, or the current thread
        if no thread is specified.
        """
        if not thread:
            thread = threading.currentThread()
        if thread in self.records:
            del self.records[thread]
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


from django.conf import settings
from utilities.io import generateUniqueFolderName
from mash.logs.models import LogEntry
from mash.logs.models import LogFile
import os


#---------------------------------------------------------------------------
# Retrieves the log files of a server (via the provided client object)
#
# @param    client      The client
# @param    log_entry   The log entry object to use, if None one is created
# @return               The log entry object
#---------------------------------------------------------------------------
def getServerLogs(client, log_entry=None, filter_list=None):
    if (client is None) or not(client.sendCommand('LOGS')):
        return None

    if log_entry is None:
        log_entry = LogEntry()
        log_entry.folder = generateUniqueFolderName()
        log_entry.save()

    fullpath = os.path.join(settings.LOG_FILES_ROOT, log_entry.folder)

    if not(os.path.exists(fullpath)):
        os.makedirs(fullpath)

    while True:
        response = client.waitResponse()
        if response.name is None:
            break

        if (response.name != "LOG_FILE") or (response.parameters is None) or (len(response.parameters) != 2):
            break

        size = int(response.parameters[1])

        content = client.waitData(size)
        if content is None:
            break

        if (filter_list is None) or (response.parameters[0] in filter_list):
            saveLogFile(log_entry, response.parameters[0], content)
    
    return log_entry


#---------------------------------------------------------------------------
# Save the content of a buffer in a log file
#
# @param log_entry  The log entry
# @param filename   Name of the file to write
# @param content    Content of the log file
#---------------------------------------------------------------------------
def saveLogFile(log_entry, filename, content):
    fullpath = os.path.join(settings.LOG_FILES_ROOT, log_entry.folder)
    
    if not(os.path.exists(fullpath)):
        os.makedirs(fullpath)

    prefix = filename[:filename.find('.log')]

    nb = log_entry.files.filter(file__startswith=prefix).count()
    
    if nb > 0:
        filename = '%s%d.log' % (prefix, nb + 1)
    
    out_file = open(os.path.join(fullpath, filename), 'w')
    out_file.write(content)
    out_file.close()
    
    log_file       = LogFile()
    log_file.entry = log_entry
    log_file.file  = filename
    log_file.save()

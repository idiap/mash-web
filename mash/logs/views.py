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


from logs.models import LogFile
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from django.conf import settings
import os


#---------------------------------------------------------------------------------------------------
# Display a log file
#---------------------------------------------------------------------------------------------------
def log(request, log_id):

    # Check that the user has the right to see the log files
    if request.user.is_anonymous() or not(request.user.get_profile().project_member):
        raise Http404
        
    # Retrieve the log file object
    log_file = get_object_or_404(LogFile, pk=log_id)
    
    # Retrieve its content
    inFile = open(os.path.join(settings.LOG_FILES_ROOT, log_file.fullpath()), 'r')

    inFile.seek(0, os.SEEK_END)
    size = inFile.tell()
    
    max_size = 200 * 1024

    if size > max_size:
        inFile.seek(-max_size + 4, os.SEEK_END)
    else:
        inFile.seek(0, os.SEEK_SET)

    content = inFile.read()
    inFile.close()

    if size > max_size:
        content = '...\n' + content

    # Rendering
    return render_to_response('logs/log.html',
                              {'content': content,
                               'filename': log_file.file, 
                              },
                              context_instance=RequestContext(request))

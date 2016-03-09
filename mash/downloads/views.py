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
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Context, loader
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from downloads.models import DownloadEntry


#---------------------------------------------------------------------------------------------------
# Display the list of the heuristics (eventually sorted and filtered)
#---------------------------------------------------------------------------------------------------
def index(request):

    public_entries = DownloadEntry.objects.filter(public=True)
    
    if not(request.user.is_anonymous()) and request.user.get_profile().project_member:
        private_entries = DownloadEntry.objects.filter(public=False)
    else:
        private_entries = None

    # Render the page
    return render_to_response('downloads/index.html',
                              { 'public_entries': public_entries,
                                'private_entries': private_entries,
                              },
                              context_instance=RequestContext(request))

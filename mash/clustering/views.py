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
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, Http404
from mash.heuristics.models import Heuristic
import xml.dom.minidom
import os


#---------------------------------------------------------------------------------------------------
# Display the heuristics space
#---------------------------------------------------------------------------------------------------
def clustering(request):

    # MIXMOD
    mixmod_html = ''
    try:
        inFile = open(os.path.join(settings.SNIPPETS_ROOT, 'clustering', 'mixmod.dat'))
        lines = inFile.read().split('\n')
        inFile.close()

        clusters = {}
        for line in lines:
            if line.startswith('<CONSTRUCT-TABLE>'):
                continue

            if len(line) == 0:
                continue

            infos = filter(lambda x: len(x), line.split(' '))

            cluster_id = int(infos[1])
            heuristic = infos[0].lower()

            if not(clusters.has_key(cluster_id)):
                clusters[cluster_id] = []

            clusters[cluster_id].append(heuristic)

        for cluster_id, heuristics in clusters.items():
            heuristics.sort()

        row_counter = 0
        for cluster_id, heuristics in clusters.items():
            first = True

            for heuristic in heuristics:
                mixmod_html += '            <tr class="row%d">\n' % ((row_counter % 2) + 1)
                mixmod_html += '                <td><a href="/heuristics/view/%s">%s</a></td>\n' % (heuristic, heuristic)

                if first:
                    mixmod_html += '                <td class="cluster" rowspan="%d">%d</td>\n' % (len(heuristics), cluster_id)
                    first = False

                mixmod_html += '            </tr>\n'

            row_counter += 1
    except:
        mixmod_html = None

    # Rendering
    return render_to_response('clustering/clustering.html',
                              { 'mixmod_html': mixmod_html,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Return a filtered version of the clustering results file using the algorithm 'rvcluster'
#---------------------------------------------------------------------------------------------------
def results_rvcluster(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404
    
    # Load the document
    xmlDocument = xml.dom.minidom.parse(os.path.join(settings.SNIPPETS_ROOT, 'clustering', 'rvcluster.dat'))
    xmlNodes = xmlDocument.getElementsByTagName('nodes')[0]

    # Remove the edges
    try:
        xmlEdges = xmlDocument.getElementsByTagName('edges')[0]
        xmlEdges.parentNode.removeChild(xmlEdges)
    except:
        pass
    
    # Retrieve all the public heuristic versions (latest only)
    try:
        public_heuristics = map(lambda x: x.latest_public_version, Heuristic.objects.filter(latest_public_version__isnull=False))
    except:
        public_heuristics = []

    # Retrieve the heuristics from the user
    try:
        user_heuristics = map(lambda x: x.latest_version(), filter(lambda x: x.latest_version() is not None, Heuristic.objects.filter(author=request.user)))
    except:
        user_heuristics = []

    # Retrieve the reference heuristic version if needed
    try:
        reference_heuristic = HeuristicVersion.objects.get(id=int(request.GET['heuristic'])).absolutename()
    except:
        reference_heuristic = None

    public_heuristics_names = map(lambda x: x.absolutename(), public_heuristics)
    public_user_heuristics_names = map(lambda x: x.absolutename(), filter(lambda x: x.heuristic.author == request.user, public_heuristics))
    user_heuristics_names = map(lambda x: x.absolutename(), user_heuristics)
    
    # Remove all the heuristic versions that the user can't see
    xmlHeuristic = None
    for xmlNode in xmlNodes.getElementsByTagName('node'):
        todelete = True

        if xmlNode.getAttribute('label') in public_heuristics_names:
            todelete = False
            xmlNode.setAttribute('public', 'true')

            if xmlNode.getAttribute('label') in public_user_heuristics_names:
                xmlNode.setAttribute('user', 'true')

        if xmlNode.getAttribute('label') in user_heuristics_names:
            todelete = False
            xmlNode.setAttribute('user', 'true')

        if (reference_heuristic is not None) and (xmlHeuristic is None) and (xmlNode.getAttribute('label') == reference_heuristic):
            xmlHeuristic = xmlNode
            
        if todelete:
            xmlNodes.removeChild(xmlNode)

    # Compute the distances between each heuristic and the reference one
    if xmlHeuristic is not None:
        xmlPosition = xmlHeuristic.getElementsByTagName('viz:position')[0]
        ref_pos = (float(xmlPosition.getAttribute('x')), float(xmlPosition.getAttribute('y')))

        for xmlNode in xmlNodes.getElementsByTagName('node'):
            xmlPosition = xmlNode.getElementsByTagName('viz:position')[0]
            pos = (float(xmlPosition.getAttribute('x')), float(xmlPosition.getAttribute('y')))
            dist = (pos[0] - ref_pos[0])**2 + (pos[1] - ref_pos[1])**2
            xmlNode.setAttribute('dist', str(dist))

    # Return the filtered document
    return HttpResponse(xmlDocument.toxml("utf-8"), mimetype="text/xml")

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
from django.template import RequestContext, Context
from django.db.models import Q
from mash.experiments.models import Experiment, Configuration
import math


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

NB_EXPERIMENTS_PER_PAGE             = 50
PAGES_NAVIGATION_BORDER_COUNT       = 5
PAGES_NAVIGATION_PREV_NEXT_COUNT    = 3

INITIALS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

SORT_KEYS = { 'u': 'user__username', 'n': 'name', 'c': 'creation_date', 's': 'start', 'd': 'duration',
              't': 'configuration__task__name', 'h': 'heuristics_count', 'p': 'predictor' }


####################################################################################################
#
# EXPERIMENTS LIST MANAGEMENT
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Represents an entry in the header of the table containing the list of experiments
#---------------------------------------------------------------------------------------------------
class HeaderEntry:

    def __init__(self, label, sort_key=None):
        self.label = label
        self.sort_key = sort_key


#---------------------------------------------------------------------------------------------------
# Holds the configuration used to customize the look and the behavior of a list of experiments
#---------------------------------------------------------------------------------------------------
class ListConfiguration:
    
    #-----------------------------------------------------------------------------------------------
    # Constructor
    #-----------------------------------------------------------------------------------------------
    def __init__(self, request, experiments_type, user=None):
        self.header_entries     = []
        self.url                = ''
        self.request            = request
        
        # Settings modifying the number of experiments in the list
        self.experiments_type   = experiments_type
        self.user               = user
        self.initial            = None
        self.query              = None

        # Settings modifying the order of the experiments in the list
        self.sort_key           = 'c'
        self.sort_ordering      = 'd'
        self.start              = 0

        self._initQuerySettings(request)
        self._initSortingSettings(request)


    #-----------------------------------------------------------------------------------------------
    # Add an entry in the header of the table containing the list of experiments
    #-----------------------------------------------------------------------------------------------
    def addHeaderEntry(self, entry):
        self.header_entries.append(entry)


    #-----------------------------------------------------------------------------------------------
    # Initialize the settings determining the number of experiments in the list from the parameters
    # of the request
    #-----------------------------------------------------------------------------------------------
    def _initQuerySettings(self, request):
        # Initial of the name of the experiment
        if request.GET.has_key('i'):
            self.initial = request.GET['i']
            if not(self.initial.upper() in INITIALS):
                self.initial = None

        # Query entered in the textfield
        if request.POST.has_key('query'):
            self.query = request.POST['query']
            if self.query in [ u'Search\u2026', u'Search...', 'Search...' ]:
                self.query = None

        # Query in the parameters
        if (self.query is None) and request.GET.has_key('q'):
            self.query = request.GET['q']


    #-----------------------------------------------------------------------------------------------
    # Initialize the settings determining the order of the experiments in the list from the parameters
    # of the request
    #-----------------------------------------------------------------------------------------------
    def _initSortingSettings(self, request):
        # Sort key
        if request.GET.has_key('sk'):
            self.sort_key = request.GET['sk']
            if (len(self.sort_key) != 1) or not(SORT_KEYS.has_key(self.sort_key)):
                self.sort_key = 'c'

        # Ordering (ascendant or descendant)
        if request.GET.has_key('so'):
            self.sort_ordering = request.GET['so']
            if (self.sort_ordering != 'a') and (self.sort_ordering != 'd'):
                if (self.sort_key == 'c') or (self.sort_key == 's'):
                    self.sort_ordering = 'd'
                else:
                    self.sort_ordering = 'a'

        # Start index (when the list spans on multiple pages)
        if request.GET.has_key('s'):
            try:
                self.start = int(request.GET['s'])
                self.start = (self.start / NB_EXPERIMENTS_PER_PAGE) * NB_EXPERIMENTS_PER_PAGE
            except:
                pass


    #-----------------------------------------------------------------------------------------------
    # Set the prefix of all the URLs that will be returned by the configuration from now
    #-----------------------------------------------------------------------------------------------
    def setupUrls(self, url, *args):
        self.url = self._buildUrl(url, *args)
    
    
    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the navigation links
    #-----------------------------------------------------------------------------------------------
    def navigationUrl(self):

        args = {'i': self.initial,
                'q': self.query,
                'sk': self.sort_key,
                'so': self.sort_ordering,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the links used to sort the list (in the header of the table)
    #-----------------------------------------------------------------------------------------------
    def headerUrl(self):
        
        args = {'i': self.initial,
                'q': self.query,
                's': self.start,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the links used to restrict the list to the experiments beginning with
    # a certain initial
    #-----------------------------------------------------------------------------------------------
    def initialsUrl(self):

        args = {'q': self.query,
                'sk': self.sort_key,
                'so': self.sort_ordering,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the query box
    #-----------------------------------------------------------------------------------------------
    def queryUrl(self):

        args = {'i': self.initial,
                'sk': self.sort_key,
                'so': self.sort_ordering,
               }

        return self._buildUrl(self.url, args)


    #---------------------------------------------------------------------------------------------------
    # Used to build an URL with a list of arguments (url?arg1=val1&arg2=val2...)
    #---------------------------------------------------------------------------------------------------
    def _buildUrl(self, url, *args):

        first = (url.find('?') < 0)

        for arg in args:

            if isinstance(arg, str) or isinstance(arg, unicode):
                if len(arg) > 0:
                    if first:
                        url += '?' + arg
                        first = False
                    else:
                        url += '&' + arg
            else:
                if len(arg) > 0:
                    for (name, value) in arg.items():
                        if value is not None:
                            if first:
                                url += '?' + name + '=' + str(value)
                                first = False
                            else:
                                url += '&' + name + '=' + str(value)

        return url


#---------------------------------------------------------------------------------------------------
# Can render a list of experiments with a specific configuration
#---------------------------------------------------------------------------------------------------
class ListRenderer:
    
    #---------------------------------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------------------------------
    def __init__(self, configuration):
        self.configuration = configuration
    
    
    #---------------------------------------------------------------------------------------------------
    # Render a list of experiments
    #---------------------------------------------------------------------------------------------------
    def renderExperimentsList(self, additional_args=''):

        # Retrieve the experiments
        (experiments, nb_experiments, current_page, nb_pages) = self._getExperimentsList()
        
        self.configuration.setupUrls(self.configuration.request.path, additional_args)

        # Set the list title
        title = 'Unknown experiments'
        if self.configuration.experiments_type == Configuration.PUBLIC:
            title = 'Public experiments'
        elif self.configuration.experiments_type == Configuration.CONSORTIUM:
            title = 'Consortium experiments'
        elif self.configuration.experiments_type == Configuration.PRIVATE:
            title = "Private experiments of '%s'" % self.configuration.user.username
        elif self.configuration.experiments_type == Configuration.CONTEST_BASE:
            title = 'Contest experiments'

        # Render the page
        return render_to_response('experiments/list.html',
                                  {'configuration': self.configuration,
                                   'title': title,
                                   'letters': INITIALS,
                                   'current_page': current_page,
                                   'nb_pages': nb_pages,
                                   'multiple_pages': (nb_pages > 1),
                                   'pages_navigation': self._getHTMLPagesNavigationControl(current_page, nb_pages),
                                   'nb_experiments': nb_experiments,
                                   'nb_experiments_per_page': NB_EXPERIMENTS_PER_PAGE,
                                   'table_header': self._getHTMLTableHeader(),
                                   'experiments': experiments,
                                   'display_username': (self.configuration.experiments_type == Configuration.CONSORTIUM),
                                  },
                                  context_instance=RequestContext(self.configuration.request))


    #---------------------------------------------------------------------------------------------------
    # Returns the list of experiments to display, according to the configuration
    #---------------------------------------------------------------------------------------------------
    def _getExperimentsList(self):
    
        # Compute the sort key
        actual_sort_key = SORT_KEYS[self.configuration.sort_key]
        if self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        # Retrieve the experiments from the database
        queryset = Experiment.objects.exclude(status=Experiment.STATUS_DELETED)
        
        queryset = queryset.filter(configuration__experiment_type=self.configuration.experiments_type)
        if self.configuration.experiments_type == Configuration.PRIVATE:
            queryset = queryset.filter(user=self.configuration.user)

        if self.configuration.query is not None:
            queryset = queryset.filter(Q(user__username__search=self.configuration.query) |
                                       Q(name__search=self.configuration.query) |
                                       Q(user__username__icontains=self.configuration.query) |
                                       Q(name__icontains=self.configuration.query))            

        if self.configuration.initial is not None:
            queryset = queryset.filter(name__istartswith=self.configuration.initial)

        if (actual_sort_key == 'duration') or (actual_sort_key == '-duration'):
            queryset = queryset.extra(select={'computed_duration': "end - start"})
            actual_sort_key = actual_sort_key.replace('duration', 'computed_duration')

        if (actual_sort_key == 'heuristics_count') or (actual_sort_key == '-heuristics_count'):
            queryset = queryset.extra(select={'heuristics_count': "SELECT COUNT(*) FROM experiments_configuration_heuristics_set AS hs WHERE hs.configuration_id=experiments_experiment.configuration_id"})

        queryset = queryset.extra(select={'predictor': "SELECT s.value FROM experiments_setting AS s WHERE s.configuration_id=experiments_experiment.configuration_id AND s.name='USE_PREDICTOR'"})

        experiments = queryset.order_by(actual_sort_key)
        
        return self._setupPages(experiments)


    def _setupPages(self, queryset):
        nb_items = queryset.count()

        items = queryset[self.configuration.start:self.configuration.start+NB_EXPERIMENTS_PER_PAGE]

        # Compute the current page and their count
        if self.configuration.start >= nb_items:
            self.configuration.start = (nb_items / NB_EXPERIMENTS_PER_PAGE) * NB_EXPERIMENTS_PER_PAGE

        current_page = (self.configuration.start / NB_EXPERIMENTS_PER_PAGE) + 1
        nb_pages = int(math.ceil(float(nb_items) / NB_EXPERIMENTS_PER_PAGE))

        # Return the results
        return (items, nb_items, current_page, nb_pages)


    #---------------------------------------------------------------------------------------------------
    # Returns the HTML code of the header of the table containing the list
    #---------------------------------------------------------------------------------------------------
    def _getHTMLTableHeader(self):
        html = '<tr>\n'

        for entry in self.configuration.header_entries:
            if entry.sort_key is None:
                html += '<th>%s</th>\n' % entry.label
            elif (entry.sort_key == self.configuration.sort_key) and (self.configuration.sort_ordering == 'd'):
                html += '<th><a href="%s&sk=%s&so=a">%s</a></th>\n' % (self.configuration.headerUrl(), entry.sort_key, entry.label)
            else:
                html += '<th><a href="%s&sk=%s&so=d">%s</a></th>\n' % (self.configuration.headerUrl(), entry.sort_key, entry.label)

        html += '</tr>\n'

        return html
        

    #---------------------------------------------------------------------------------------------------
    # Returns the HTML code of the pages navigation control on the heuristics list page
    #---------------------------------------------------------------------------------------------------
    def _getHTMLPagesNavigationControl(self, current_page, nb_pages):

        url = self.configuration.navigationUrl()

        html = '<span id="pages_nav">'

        if nb_pages <= PAGES_NAVIGATION_BORDER_COUNT:
            for i in range(0, nb_pages):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { 's': str(i * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        elif current_page < PAGES_NAVIGATION_PREV_NEXT_COUNT:
            for i in range(0, PAGES_NAVIGATION_BORDER_COUNT):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { 's': str(i * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

            if nb_pages > PAGES_NAVIGATION_BORDER_COUNT + 1:
                html += '...'

            html += '<a href="' + self.configuration._buildUrl(url, { 's': str((nb_pages - 1) * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(nb_pages) + '</a>'

        elif current_page <= PAGES_NAVIGATION_BORDER_COUNT:
            max = current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT
            if max > nb_pages:
                max = nb_pages

            for i in range(0, max):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { 's': str(i * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

            if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT:
                if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
                    html += '...'

                html += '<a href="' + self.configuration._buildUrl(url, { 's': str((nb_pages - 1) * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(nb_pages) + '</a>'

        elif current_page > nb_pages - PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
            if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 0:
                html += '<a href="' + url + '&s=0">1</a>'

                if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 1:
                    html += '...'

            for i in range(nb_pages - PAGES_NAVIGATION_BORDER_COUNT, nb_pages):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { 's': str(i * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        elif current_page > nb_pages - PAGES_NAVIGATION_BORDER_COUNT:
            if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 0:
                html += '<a href="' + url + '&s=0">1</a>'

                if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 1:
                    html += '...'

            for i in range(current_page - PAGES_NAVIGATION_PREV_NEXT_COUNT - 1, nb_pages):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { 's': str(i * NB_EXPERIMENTS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        html += '</span>'

        return html


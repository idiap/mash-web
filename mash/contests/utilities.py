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
from django.template import Context, loader
from django.db.models import Q
from contests.models import Contest, ContestEntry
import math
from datetime import datetime


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

class Constants:

    # Sort keys - Contests
    SORT_KEY_NAME           = 'n'
    SORT_KEY_NB_ENTRIES     = 'c'
    SORT_KEY_BEST_ENTRY     = 'f'
    SORT_KEY_START_DATE     = 's'
    SORT_KEY_END_DATE       = 'e'

    # Sort keys - Contest entries
    SORT_KEY_RANK           = 'r'
    SORT_KEY_HEURISTIC      = 'h'
    SORT_KEY_EXPERIMENT     = 'x'
    SORT_KEY_JOIN_DATE      = 'j'

    SORT_KEYS = {
        SORT_KEY_NAME:          'name',
        SORT_KEY_NB_ENTRIES:    'entries_count',
        SORT_KEY_BEST_ENTRY:    'best_entry_name',
        SORT_KEY_START_DATE:    'start',
        SORT_KEY_END_DATE:      'end',
        SORT_KEY_RANK:          'rank',
        SORT_KEY_HEURISTIC:     'heuristic_name',
        SORT_KEY_EXPERIMENT:    'experiment__name',
        SORT_KEY_JOIN_DATE:     'experiment__creation_date',
    }

    CONTEST_CONTRIBUTORS_ENTRIES    = 0
    CONTEST_CONSORTIUM_ENTRIES      = 1
    CONTEST_TYPE_FINISHED           = 2
    CONTEST_TYPE_IN_PROGRESS        = 3
    CONTEST_TYPE_FUTURE             = 4

    SORT_KEYS_PREFIXES = {
        CONTEST_CONTRIBUTORS_ENTRIES:   'u',
        CONTEST_CONSORTIUM_ENTRIES:     'c',
        CONTEST_TYPE_FINISHED:          'd',
        CONTEST_TYPE_IN_PROGRESS:       'p',
        CONTEST_TYPE_FUTURE:            'f',
    }


####################################################################################################
#
# CONTESTS LIST MANAGEMENT
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Represents an entry in the header of the table containing the list of contests
#---------------------------------------------------------------------------------------------------
class HeaderEntry:

    def __init__(self, label, sort_key=None):
        self.label = label
        self.sort_key = sort_key


#---------------------------------------------------------------------------------------------------
# Holds the configuration used to customize the look and the behavior of a list of contests or
# contest entries
#---------------------------------------------------------------------------------------------------
class ListConfiguration:
    
    #-----------------------------------------------------------------------------------------------
    # Constructor
    #-----------------------------------------------------------------------------------------------
    def __init__(self, request, list_type, contest=None):
        self.header_entries        = []
        self.url                   = ''
        self.request               = request
        self.list_type             = list_type
        self.contest               = contest
        self.improvement_reference = None

        # Settings modifying the order of the elements in the list
        if (self.list_type == Constants.CONTEST_CONTRIBUTORS_ENTRIES) or \
           (self.list_type == Constants.CONTEST_CONSORTIUM_ENTRIES):
            self.sort_key       = Constants.SORT_KEY_RANK
            self.sort_ordering  = 'a'
        else:
            self.sort_key       = Constants.SORT_KEY_START_DATE
            self.sort_ordering  = 'd'

        self.other_sort_args = []
            
        self._initSortingSettings(request)


    #-----------------------------------------------------------------------------------------------
    # Add an entry in the header of the table containing the list of experiments
    #-----------------------------------------------------------------------------------------------
    def addHeaderEntry(self, entry):
        self.header_entries.append(entry)


    #-----------------------------------------------------------------------------------------------
    # Initialize the settings determining the order of the contests in the list from the parameters
    # of the request
    #-----------------------------------------------------------------------------------------------
    def _initSortingSettings(self, request):
        prefix = Constants.SORT_KEYS_PREFIXES[self.list_type]

        # Sort key
        if request.GET.has_key(prefix + 'sk'):
            self.sort_key = request.GET[prefix + 'sk']
            if (len(self.sort_key) != 1) or not(Constants.SORT_KEYS.has_key(self.sort_key)):
                if (self.list_type == Constants.CONTEST_CONTRIBUTORS_ENTRIES) or \
                   (self.list_type == Constants.CONTEST_CONSORTIUM_ENTRIES):
                    self.sort_key = Constants.SORT_KEY_RANK
                else:
                    self.sort_key = Constants.SORT_KEY_START_DATE

        # Ordering (ascendant or descendant)
        if request.GET.has_key(prefix + 'so'):
            self.sort_ordering = request.GET[prefix + 'so']
            if (self.sort_ordering != 'a') and (self.sort_ordering != 'd'):
                if (self.sort_key == Constants.SORT_KEY_JOIN_DATE) or \
                   (self.sort_key == Constants.SORT_KEY_START_DATE) or \
                   (self.sort_key == Constants.SORT_KEY_END_DATE):
                    self.sort_ordering = 'd'
                else:
                    self.sort_ordering = 'a'

        for (name, value) in request.GET.items():
            l = {}
            if name not in (prefix + 'sk', prefix + 'so'):
                l[name] = value
            if len(l) > 0:
                self.other_sort_args.append(l)
        

    #-----------------------------------------------------------------------------------------------
    # Set the prefix of all the URLs that will be returned by the configuration from now
    #-----------------------------------------------------------------------------------------------
    def setupUrls(self, url, list_id, *args):
        self.url = self._buildUrl(url, None, *args)
        self.list_id = list_id
    
    
    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the links used to sort the list (in the header of the table)
    #-----------------------------------------------------------------------------------------------
    def headerUrl(self, args):
        return self._buildUrl(self.url, self.list_id, args)


    #-----------------------------------------------------------------------------------------------
    # Used to build an URL with a list of arguments (url?arg1=val1&arg2=val2...)
    #-----------------------------------------------------------------------------------------------
    def _buildUrl(self, url, list_id, *args):

        def _process_args(url, args):
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

        url = _process_args(url, args)
        
        if (list_id is not None) and (len(list_id) > 0):
            url = _process_args(url, self.other_sort_args)
            url += '#%s' % list_id

        return url


#---------------------------------------------------------------------------------------------------
# Can render a list of contests or contest entries with a specific configuration
#---------------------------------------------------------------------------------------------------
class ListRenderer:
    
    #-----------------------------------------------------------------------------------------------
    # Constructor
    #-----------------------------------------------------------------------------------------------
    def __init__(self, configuration):
        self.configuration = configuration
    

    #-----------------------------------------------------------------------------------------------
    # Render the list
    #-----------------------------------------------------------------------------------------------
    def render(self, additional_args=''):

        if (self.configuration.list_type == Constants.CONTEST_CONTRIBUTORS_ENTRIES) or \
           (self.configuration.list_type == Constants.CONTEST_CONSORTIUM_ENTRIES):
            return self._renderContestEntriesList(additional_args)
        else:
            return self._renderContestsList(additional_args)

    
    #-----------------------------------------------------------------------------------------------
    # Render a list of contests
    #-----------------------------------------------------------------------------------------------
    def _renderContestsList(self, additional_args=''):

        # Retrieve the contests
        contests = self._getContestsList()
        if len(contests) == 0:
            return None
        
        # Set the list title
        if self.configuration.list_type == Constants.CONTEST_TYPE_FINISHED:
            title = 'Previous contests'
            list_id = 'previous_contests'
        elif self.configuration.list_type == Constants.CONTEST_TYPE_IN_PROGRESS:
            title = 'Current contests'
            list_id = 'current_contests'
        elif self.configuration.list_type == Constants.CONTEST_TYPE_FUTURE:
            title = 'Future contests'
            list_id = 'future_contests'

        self.configuration.setupUrls(self.configuration.request.path, list_id, additional_args)

        # Prepare the context
        context = Context({'configuration': self.configuration,
                           'title': title,
                           'list_id': list_id,
                           'table_header': self._getHTMLTableHeader(),
                           'contests': contests,
                           'request': self.configuration.request,
                          })

        # Render the page
        template = loader.get_template('contests/embedded_contests_list.html')
        return template.render(context)


    #-----------------------------------------------------------------------------------------------
    # Render a list of contest entries
    #-----------------------------------------------------------------------------------------------
    def _renderContestEntriesList(self, additional_args=''):

        # Retrieve the contests
        entries = self._getContestEntriesList()
        if len(entries) == 0:
            return None

        # Set the list title
        if self.configuration.list_type == Constants.CONTEST_CONTRIBUTORS_ENTRIES:
            title = 'Entries'
            list_id = 'contributors_entries'
        else:
            title = 'Consortium entries'
            list_id = 'consortium_entries'

        self.configuration.setupUrls(self.configuration.request.path, list_id, additional_args)

        # Prepare the context
        context = Context({'configuration': self.configuration,
                           'title': title,
                           'list_id': list_id,
                           'table_header': self._getHTMLTableHeader(),
                           'entries': entries,
                           'request': self.configuration.request,
                          })

        # Render the page
        template = loader.get_template('contests/embedded_contest_entries_list.html')
        return template.render(context)


    #-----------------------------------------------------------------------------------------------
    # Returns the list of contests to display, according to the configuration
    #-----------------------------------------------------------------------------------------------
    def _getContestsList(self):
    
        # Compute the sort key
        actual_sort_key = Constants.SORT_KEYS[self.configuration.sort_key]
        if self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        secondary_sort_key = None
        if self.configuration.sort_key == Constants.SORT_KEY_START_DATE:
            secondary_sort_key = Constants.SORT_KEYS[Constants.SORT_KEY_END_DATE]
            if self.configuration.sort_ordering == 'd':
                secondary_sort_key = '-' + secondary_sort_key

        elif self.configuration.sort_key == Constants.SORT_KEY_END_DATE:
            secondary_sort_key = Constants.SORT_KEYS[Constants.SORT_KEY_START_DATE]
            if self.configuration.sort_ordering == 'd':
                secondary_sort_key = '-' + secondary_sort_key

        # Retrieve the contests from the database
        now = datetime.now()
        if self.configuration.list_type == Constants.CONTEST_TYPE_FINISHED:
            queryset = Contest.objects.exclude(end__isnull=True).filter(end__lt=now)
        elif self.configuration.list_type == Constants.CONTEST_TYPE_IN_PROGRESS:
            queryset = Contest.objects.filter(start__lte=now).filter(Q(end__isnull=True) | Q(end__gt=now))
        elif self.configuration.list_type == Constants.CONTEST_TYPE_FUTURE:
            queryset = Contest.objects.filter(start__gt=now)

        queryset = queryset.extra(select={
            'best_entry_name': "SELECT LOWER(CONCAT(u.username, '/', h.name, '/', CAST(v.version AS CHAR))) " \
                                 "FROM contests_contestentry AS ce, " \
                                      "heuristics_heuristicversion AS v, " \
                                      "heuristics_heuristic AS h, " \
                                      "auth_user AS u, " \
                                      "accounts_userprofile AS p " \
                                "WHERE ce.contest_id=contests_contest.id " \
                                  "AND ce.rank=1 " \
                                  "AND ce.heuristic_version_id=v.id " \
                                  "AND v.heuristic_id=h.id " \
                                  "AND h.author_id=u.id " \
                                  "AND p.user_id=u.id " \
                                  "AND p.project_member=0",
                                  
            'entries_count': "SELECT COUNT(*) " \
                               "FROM contests_contestentry AS ce, " \
                                    "heuristics_heuristicversion AS v, " \
                                    "heuristics_heuristic AS h, " \
                                    "accounts_userprofile AS p " \
                              "WHERE ce.contest_id=contests_contest.id " \
                                "AND ce.heuristic_version_id=v.id " \
                                "AND v.heuristic_id=h.id " \
                                "AND p.user_id=h.author_id " \
                                "AND p.project_member=0",
        })
        
        queryset = queryset.order_by(actual_sort_key)
        
        if secondary_sort_key is not None:
            queryset = queryset.order_by(secondary_sort_key)

        return queryset


    #-----------------------------------------------------------------------------------------------
    # Returns the list of contest entries to display, according to the configuration
    #-----------------------------------------------------------------------------------------------
    def _getContestEntriesList(self):

        # Compute the sort key
        actual_sort_key = Constants.SORT_KEYS[self.configuration.sort_key]
        if self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        # Retrieve the contest entries from the database
        if self.configuration.list_type == Constants.CONTEST_CONTRIBUTORS_ENTRIES:
            queryset = self.configuration.contest.entries.filter(heuristic_version__heuristic__author__userprofile__project_member=False)
        else:
            queryset = self.configuration.contest.entries.filter(heuristic_version__heuristic__author__userprofile__project_member=True)

        queryset = queryset.extra(select={
            'heuristic_name': "SELECT LOWER(CONCAT(u.username, '/', h.name, '/', CAST(v.version AS CHAR))) " \
                                "FROM heuristics_heuristicversion AS v, " \
                                     "heuristics_heuristic AS h, " \
                                     "auth_user AS u " \
                               "WHERE contests_contestentry.heuristic_version_id=v.id " \
                                 "AND v.heuristic_id=h.id " \
                                 "AND h.author_id=u.id"
        })

        if self.configuration.improvement_reference:
            queryset = queryset.extra(select={
                'improvement': "SELECT 100 * (r.test_error - %s) " \
                                 "FROM experiments_classificationresults AS r " \
                                "WHERE contests_contestentry.experiment_id=r.experiment_id" % self.configuration.improvement_reference
            })
        
        if self.configuration.sort_key == Constants.SORT_KEY_RANK:
            queryset = queryset.extra(select={'null_rank': 'contests_contestentry.rank is null'})
            queryset = queryset.extra(order_by=['null_rank', actual_sort_key])
        elif self.configuration.sort_key == Constants.SORT_KEY_JOIN_DATE:
            secondary_sort_key = Constants.SORT_KEYS[Constants.SORT_KEY_RANK]
            if self.configuration.sort_ordering == 'd':
                secondary_sort_key = '-' + secondary_sort_key

            queryset = queryset.extra(select={'null_rank': 'contests_contestentry.rank is null'})
            queryset = queryset.extra(order_by=[actual_sort_key, 'null_rank', secondary_sort_key])
        else:
            queryset = queryset.order_by(actual_sort_key)

        return queryset


    #-----------------------------------------------------------------------------------------------
    # Returns the HTML code of the header of the table containing the list
    #-----------------------------------------------------------------------------------------------
    def _getHTMLTableHeader(self):
        prefix = Constants.SORT_KEYS_PREFIXES[self.configuration.list_type]
 
        html = '<tr>\n'

        for entry in self.configuration.header_entries:
            if entry.sort_key is None:
                html += '<th>%s</th>\n' % entry.label
            else:
                args = {}
                args[prefix + 'sk'] = entry.sort_key
                args[prefix + 'so'] = 'd'
                
                if (entry.sort_key == self.configuration.sort_key) and (self.configuration.sort_ordering == 'd'):
                    args[prefix + 'so'] = 'a'
                
                html += '<th><a href="%s">%s</a></th>\n' % (self.configuration.headerUrl(args), entry.label)

        html += '</tr>\n'

        return html

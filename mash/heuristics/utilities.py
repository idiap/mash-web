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
from django.template import Context, loader
from django.db.models import Q
from django.contrib.flatpages.models import FlatPage
from mash.heuristics.models import Heuristic, HeuristicVersion
from pymash.gitrepository import GitRepository
from texts_db.models import Text
from pygments import highlight
from pygments.lexers import CppLexer
from pygments.formatters import HtmlFormatter
import math
import os


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

NB_HEURISTICS_PER_PAGE              = 50
PAGES_NAVIGATION_BORDER_COUNT       = 5
PAGES_NAVIGATION_PREV_NEXT_COUNT    = 3

INITIALS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

SORT_KEYS = { 'u': 'author__username', 'n': 'name', 'r': '%s__rank', 'v': 'visible_versions_count', 'd': '%s__upload_date', 'a': '%s__public' }
SORT_KEYS_VERSIONS = { 'v': 'version', 'r': 'rank', 'd': 'upload_date', 'a': 'public' }

HEURISTICS_LINK_NONE            = 0
HEURISTICS_LINK_VERSIONS        = 1
HEURISTICS_LINK_MODIFICATION    = 2


####################################################################################################
#
# HEURISTICS LIST MANAGEMENT
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Represents an entry in the header of the table containing the list of heuristics
#---------------------------------------------------------------------------------------------------
class HeaderEntry:

    def __init__(self, label, sort_key=None, condition=None):
        self.label = label
        self.sort_key = sort_key
        self.condition = condition


#---------------------------------------------------------------------------------------------------
# Contains all the informations needed to display a list of heuristics in a certain mode.
# Instances of this class are considered to be immutable: the possible actions in a specific mode
# are always the same. See ListConfiguration for the customization of a list.
#---------------------------------------------------------------------------------------------------
class Mode:
    
    def __init__(self):
        self.header_entries = []
        self.title = ''
        self.list_template = ''
        self.sort_key_prefix = None
        self.relate_to_any_user = True
        self.can_upload = True
        self.can_select = False
        self.can_diff = False
        self.can_query = True
        self.can_display_all_heuristics = True
        self.can_display_own_heuristics = True
        self.can_display_multiple_heuristic_versions = False
        self.can_display_tools = False
        self.can_display_accessibility = False
        self.modify_queryset = None
        
    def addHeaderEntry(self, entry):
        self.header_entries.append(entry)


MODES = []

#----- MODE_ALL_PUBLIC_HEURISTICS
def modify_queryset_for_public_heuristics(q, configuration):
    q = q.exclude(latest_public_version__isnull=True)
    q = q.exclude(latest_public_version__checked__exact=False)
    return q

mode = Mode()
mode.title = 'All the heuristics'
mode.list_template = 'heuristics/list_all_public.html'
mode.sort_key_prefix = 'latest_public_version'
mode.modify_queryset = modify_queryset_for_public_heuristics
mode.addHeaderEntry(HeaderEntry('USERNAME', sort_key='u'))
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_ALL_PUBLIC_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_OWN_PUBLIC_HEURISTICS
mode = Mode()
mode.title = 'My public heuristics'
mode.list_template = 'heuristics/list_user_public.html'
mode.sort_key_prefix = 'latest_public_version'
mode.relate_to_any_user = False
mode.can_display_tools = True
mode.modify_queryset = modify_queryset_for_public_heuristics
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))
mode.addHeaderEntry(HeaderEntry('TOOLS'))

MODE_OWN_PUBLIC_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_OWN_PRIVATE_HEURISTICS
def modify_queryset_for_private_heuristics(q, configuration):
    return q.exclude(latest_private_version__isnull=True).exclude(simple=True)

mode = Mode()
mode.title = 'My private heuristics'
mode.list_template = 'heuristics/list_user_private.html'
mode.sort_key_prefix = 'latest_private_version'
mode.relate_to_any_user = False
mode.can_display_tools = True
mode.modify_queryset = modify_queryset_for_private_heuristics
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))
mode.addHeaderEntry(HeaderEntry('TOOLS'))

MODE_OWN_PRIVATE_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_USER_PUBLIC_HEURISTICS
mode = Mode()
mode.title = "Public heuristics of '<a href=\"/accounts/profile/%d/\">%s</a>'"
mode.list_template = 'heuristics/list_user_public.html'
mode.sort_key_prefix = 'latest_public_version'
mode.relate_to_any_user = False
mode.modify_queryset = modify_queryset_for_public_heuristics
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_USER_PUBLIC_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_USER_PRIVATE_HEURISTICS
mode = Mode()
mode.title = "Private heuristics of '<a href=\"/accounts/profile/%d/\">%s</a>'"
mode.list_template = 'heuristics/list_user_private.html'
mode.sort_key_prefix = 'latest_private_version'
mode.relate_to_any_user = False
mode.modify_queryset = modify_queryset_for_private_heuristics
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_USER_PRIVATE_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_SELECT_OWN_HEURISTIC
mode = Mode()
mode.title = 'My heuristics'
mode.list_template = 'heuristics/list_selection.html'
mode.relate_to_any_user = False
mode.can_upload = False
mode.can_select = True
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.can_display_accessibility = True
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('ACCESSIBILITY', sort_key='a'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_SELECT_OWN_HEURISTIC = len(MODES)
MODES.append(mode)


#----- MODE_SELECT_HEURISTIC
def modify_queryset_for_select_heuristics(q, configuration):
    if not(configuration.request.user.is_anonymous()):
        return q.filter(Q(latest_public_version__isnull=False) | Q(author=configuration.request.user))
    else:
        return q.filter(latest_public_version__isnull=False)

mode = Mode()
mode.title = 'All the heuristics'
mode.list_template = 'heuristics/list_selection.html'
mode.can_upload = False
mode.can_select = True
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.can_display_accessibility = True
mode.modify_queryset = modify_queryset_for_select_heuristics
mode.addHeaderEntry(HeaderEntry('USERNAME', sort_key='u'))
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('# VERSIONS', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('ACCESSIBILITY', sort_key='a'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_SELECT_HEURISTIC = len(MODES)
MODES.append(mode)


#----- MODE_PUBLIC_HEURISTIC_VERSIONS
def modify_queryset_visible_heuristic_versions(q, configuration):
    if not(configuration.request.user.is_anonymous()):
        return q.filter(Q(public=True) | Q(heuristic__author=configuration.request.user))
    else:
        return q.filter(public=True)

mode = Mode()
mode.title = "All versions of heuristic '%s'"
mode.list_template = 'heuristics/list_versions.html'
mode.can_upload = False
mode.can_diff = True
mode.can_query = False
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.can_display_multiple_heuristic_versions = True
mode.modify_queryset = modify_queryset_visible_heuristic_versions
mode.addHeaderEntry(HeaderEntry('VERSION', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_PUBLIC_HEURISTIC_VERSIONS = len(MODES)
MODES.append(mode)


#----- MODE_OWN_HEURISTIC_VERSIONS
mode = Mode()
mode.title = "All versions of heuristic '%s'"
mode.list_template = 'heuristics/list_versions.html'
mode.can_upload = False
mode.can_diff = True
mode.can_query = False
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.can_display_multiple_heuristic_versions = True
mode.can_display_tools = True
mode.can_display_accessibility = True
mode.addHeaderEntry(HeaderEntry('VERSION', sort_key='v'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('ACCESSIBILITY', sort_key='a'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))
mode.addHeaderEntry(HeaderEntry('TOOLS'))

MODE_OWN_HEURISTIC_VERSIONS = len(MODES)
MODES.append(mode)


#----- MODE_PUBLIC_DERIVED_HEURISTICS
mode = Mode()
mode.title = "All heuristics inspired by '%s'"
mode.list_template = 'heuristics/list_modifications.html'
mode.sort_key_prefix = 'latest_public_version'
mode.can_upload = False
mode.can_diff = True
mode.can_query = True
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.modify_queryset = modify_queryset_for_public_heuristics
mode.addHeaderEntry(HeaderEntry('USERNAME', sort_key='u'))
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_PUBLIC_DERIVED_HEURISTICS = len(MODES)
MODES.append(mode)


#----- MODE_ALL_DERIVED_HEURISTICS
def modify_queryset_visible_heuristics(q, configuration):
    if not(configuration.request.user.is_anonymous()):
        return q.filter(Q(latest_public_version__isnull=False) | Q(author=configuration.request.user))
    else:
        return q.filter(latest_public_version__isnull=False)

mode = Mode()
mode.title = "All heuristics inspired by '%s'"
mode.list_template = 'heuristics/list_modifications.html'
mode.sort_key_prefix = None
mode.can_upload = False
mode.can_diff = True
mode.can_query = True
mode.can_display_all_heuristics = False
mode.can_display_own_heuristics = False
mode.can_display_accessibility = True
mode.modify_queryset = modify_queryset_visible_heuristics
mode.addHeaderEntry(HeaderEntry('USERNAME', sort_key='u'))
mode.addHeaderEntry(HeaderEntry('NAME', sort_key='n'))
mode.addHeaderEntry(HeaderEntry('RANK', sort_key='r'))
mode.addHeaderEntry(HeaderEntry('ACCESSIBILITY', sort_key='a'))
mode.addHeaderEntry(HeaderEntry('DESCRIPTION'))
mode.addHeaderEntry(HeaderEntry('UPLOAD DATE', sort_key='d'))

MODE_ALL_DERIVED_HEURISTICS = len(MODES)
MODES.append(mode)


#---------------------------------------------------------------------------------------------------
# Holds the configuration used to customize the look and the behavior of a list of heuristics
#---------------------------------------------------------------------------------------------------
class ListConfiguration:
    
    #-----------------------------------------------------------------------------------------------
    # Constructor
    #-----------------------------------------------------------------------------------------------
    def __init__(self, mode, request, user=None, heuristic=None, heuristic_version=None,
                heuristics_link=HEURISTICS_LINK_NONE, search_popup=False, url_args_prefix=''):
        self.mode                   = mode
        self.url                    = self._buildUrl(request.path)
        self.url_args_prefix        = url_args_prefix
        self.request                = request
        
        # Settings modifying the number of heuristics in the list
        self.user                   = user
        self.heuristic              = heuristic
        self.heuristic_version      = heuristic_version
        self.heuristics_link        = heuristics_link
        self.initial                = None
        self.query                  = None

        if self.heuristic is None:
            self.heuristics_link = HEURISTICS_LINK_NONE
        elif self.heuristics_link == HEURISTICS_LINK_NONE:
            self.heuristic = None

        # Settings modifying the order of the heuristics in the list
        self.sort_key               = 'u'
        self.sort_ordering          = 'a'
        self.start                  = 0

        # Settings used when the list was invoked from another page to let the user choose a heuristic 
        self.search_popup           = (mode.can_select and search_popup)

        self._initQuerySettings(request)
        self._initSortingSettings(request)


    #-----------------------------------------------------------------------------------------------
    # Initialize the settings determining the number of heuristics in the list from the parameters
    # of the request
    #-----------------------------------------------------------------------------------------------
    def _initQuerySettings(self, request):
        # Initial of the name of the heuristic
        if request.GET.has_key(self.url_args_prefix + 'i'):
            self.initial = request.GET[self.url_args_prefix + 'i']
            if not(self.initial.upper() in INITIALS):
                self.initial = None

        # Query entered in the textfield
        if request.POST.has_key('query'):
            self.query = request.POST['query']
            if self.query in [ u'Search\u2026', u'Search...', 'Search...' ]:
                self.query = None

        # Query in the parameters
        if (self.query is None) and request.GET.has_key(self.url_args_prefix + 'q'):
            self.query = request.GET[self.url_args_prefix + 'q']


    #-----------------------------------------------------------------------------------------------
    # Initialize the settings determining the order of the heuristics in the list from the parameters
    # of the request
    #-----------------------------------------------------------------------------------------------
    def _initSortingSettings(self, request):
        # Sort key
        if request.GET.has_key(self.url_args_prefix + 'sk'):
            self.sort_key = request.GET[self.url_args_prefix + 'sk']
            if (len(self.sort_key) != 1) or not(SORT_KEYS.has_key(self.sort_key)):
                self.sort_key = 'u'

        # Ordering (ascendant or descendant)
        if request.GET.has_key(self.url_args_prefix + 'so'):
            self.sort_ordering = request.GET[self.url_args_prefix + 'so']
            if (self.sort_ordering != 'a') and (self.sort_ordering != 'd'):
                self.sort_ordering = 'a'

        # Start index (when the list spans on multiple pages)
        if request.GET.has_key(self.url_args_prefix + 's'):
            try:
                self.start = int(request.GET[self.url_args_prefix + 's'])
                self.start = (self.start / NB_HEURISTICS_PER_PAGE) * NB_HEURISTICS_PER_PAGE
            except:
                pass


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the navigation links
    #-----------------------------------------------------------------------------------------------
    def fullUrl(self):

        args = {self.url_args_prefix + 'i': self.initial,
                self.url_args_prefix + 'q': self.query,
                self.url_args_prefix + 'sk': self.sort_key,
                self.url_args_prefix + 'so': self.sort_ordering,
                self.url_args_prefix + 's': self.start,
               }

        return self._buildUrl(self.url, args)

    
    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the navigation links
    #-----------------------------------------------------------------------------------------------
    def navigationUrl(self):

        args = {self.url_args_prefix + 'i': self.initial,
                self.url_args_prefix + 'q': self.query,
                self.url_args_prefix + 'sk': self.sort_key,
                self.url_args_prefix + 'so': self.sort_ordering,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the links used to sort the list (in the header of the table)
    #-----------------------------------------------------------------------------------------------
    def headerUrl(self):
        
        args = {self.url_args_prefix + 'i': self.initial,
                self.url_args_prefix + 'q': self.query,
                self.url_args_prefix + 's': self.start,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the links used to restrict the list to the heuristics beginning with
    # a certain initial
    #-----------------------------------------------------------------------------------------------
    def initialsUrl(self):

        args = {self.url_args_prefix + 'q': self.query,
                self.url_args_prefix + 'sk': self.sort_key,
                self.url_args_prefix + 'so': self.sort_ordering,
               }

        return self._buildUrl(self.url, args)


    #-----------------------------------------------------------------------------------------------
    # Returns the base URL for the query box
    #-----------------------------------------------------------------------------------------------
    def queryUrl(self):

        args = {self.url_args_prefix + 'i': self.initial,
                self.url_args_prefix + 'sk': self.sort_key,
                self.url_args_prefix + 'so': self.sort_ordering,
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
# Can render a list of heuristic in a certain mode with a specific configuration
#---------------------------------------------------------------------------------------------------
class ListRenderer:
    
    #---------------------------------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------------------------------
    def __init__(self, mode, configuration):
        self.mode = mode
        self.configuration = configuration
    
    
    #---------------------------------------------------------------------------------------------------
    # Render the list in HTML format
    #---------------------------------------------------------------------------------------------------
    def render(self, request):
        if self.configuration.heuristics_link == HEURISTICS_LINK_VERSIONS:
            return self._renderHeuristicVersionsList(request)
        else:
            return self._renderHeuristicsList(request)

        
    #---------------------------------------------------------------------------------------------------
    # Render a list of heuristics in HTML format
    #---------------------------------------------------------------------------------------------------
    def _renderHeuristicsList(self, request):

        # Retrieve the heuristics
        if self.configuration.heuristics_link == HEURISTICS_LINK_MODIFICATION:
            (heuristics, nb_heuristics, current_page, nb_pages) = self._getDerivedHeuristicsList()
        else:
            (heuristics, nb_heuristics, current_page, nb_pages) = self._getHeuristicsList(request.user)


        # Modify the list title if necessary
        title = self.mode.title
        try:
            if self.configuration.user is not None:
                title = title % (self.configuration.user.id, self.configuration.user.username)
            elif self.configuration.heuristic is not None:
                title = title % self.configuration.heuristic.fullname()
        except:
            pass


        # Prepare the context
        context = Context({'mode': self.mode,
                           'configuration': self.configuration,
                           'title': title,
                           'letters': INITIALS,
                           'current_page': current_page,
                           'nb_pages': nb_pages,
                           'multiple_pages': (nb_pages > 1),
                           'pages_navigation': self._getHTMLPagesNavigationControl(current_page, nb_pages),
                           'nb_heuristics': nb_heuristics,
                           'table_header': self._getHTMLTableHeader(),
                           'heuristics': heuristics,
                           'request': request,
                          })


        # Render the list template
        template = loader.get_template('heuristics/embedded_list.html')
        html_list = template.render(context)

        
        # Return the result
        return html_list


    #---------------------------------------------------------------------------------------------------
    # Render a list of heuristics version, returns two HTML segments: one for the scripts, the other for
    # the list
    #---------------------------------------------------------------------------------------------------
    def _renderHeuristicVersionsList(self, request):

        # Retrieve the heuristics
        (versions, nb_versions, current_page, nb_pages) = self._getHeuristicVersionsList()

        # Prepare the context
        context = Context({'mode': self.mode,
                           'configuration': self.configuration,
                           'current_page': current_page,
                           'nb_pages': nb_pages,
                           'multiple_pages': (nb_pages > 1),
                           'pages_navigation': self._getHTMLPagesNavigationControl(current_page, nb_pages),
                           'nb_heuristics': nb_versions,
                           'table_header': self._getHTMLTableHeader(),
                           'versions': versions,
                           'request': request,
                          })


        # Render the list template
        template = loader.get_template('heuristics/embedded_list.html')
        html_list = template.render(context)


        # Return the result
        return html_list


    #---------------------------------------------------------------------------------------------------
    # Returns the list of heuristics to display, according to the mode and the configuration
    #---------------------------------------------------------------------------------------------------
    def _getHeuristicsList(self, user):
    
        # Compute the sort key
        actual_sort_key = SORT_KEYS[self.configuration.sort_key]
        if actual_sort_key.startswith('%s'):
            actual_sort_key = actual_sort_key % self.mode.sort_key_prefix
        if self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        # Retrieve the heuristics from the database
        queryset = Heuristic.objects.exclude(latest_public_version__isnull=True, latest_private_version__isnull=True)

        if self.configuration.user is not None:
            queryset = queryset.filter(author__id=self.configuration.user.id)

        if self.configuration.query is not None:
            queryset = queryset.filter(Q(author__username__search=self.configuration.query) |
                                       Q(name__search=self.configuration.query) |
                                       Q(description__search=self.configuration.query) |
                                       Q(author__username__icontains=self.configuration.query) |
                                       Q(name__icontains=self.configuration.query) |
                                       Q(description__icontains=self.configuration.query))

        if self.configuration.initial is not None:
            queryset = queryset.filter(name__istartswith=self.configuration.initial)

        if self.mode.modify_queryset is not None:
            queryset = self.mode.modify_queryset(queryset, self.configuration)

        if user.is_superuser or ((self.configuration.user is not None) and (user.id == self.configuration.user.id)):
            queryset = queryset.extra(select={'visible_versions_count': "SELECT COUNT(*) FROM heuristics_heuristicversion AS v " \
                                                                         "WHERE v.heuristic_id=heuristics_heuristic.id " \
                                                                           "AND v.status!='DEL'"
                                              })
        elif user.is_anonymous:
            queryset = queryset.extra(select={'visible_versions_count': "SELECT COUNT(*) FROM heuristics_heuristicversion AS v " \
                                                                         "WHERE v.heuristic_id=heuristics_heuristic.id " \
                                                                           "AND v.status!='DEL' "
                                                                           "AND v.public=1"
                                             })

        if self.configuration.sort_key == 'r':
            queryset = queryset.extra(select={'null_rank': "SELECT rank IS NULL FROM heuristics_heuristicversion AS v " \
                                                            "WHERE v.id=heuristics_heuristic.%s_id" % self.mode.sort_key_prefix})
            queryset = queryset.extra(order_by=['null_rank', actual_sort_key])
        elif self.configuration.sort_key == 'd':
            secondary_sort_key = SORT_KEYS['r'] % self.mode.sort_key_prefix
            if self.configuration.sort_ordering == 'd':
                secondary_sort_key = '-' + secondary_sort_key

            queryset = queryset.extra(select={'null_rank': "SELECT rank IS NULL FROM heuristics_heuristicversion AS v " \
                                                            "WHERE v.id=heuristics_heuristic.%s_id" % self.mode.sort_key_prefix})
            queryset = queryset.extra(order_by=[actual_sort_key, 'null_rank', secondary_sort_key])
        else:
            if self.configuration.sort_key == 'u':
                queryset = queryset.order_by('name')
            
            queryset = queryset.order_by(actual_sort_key)

        return self._setupPages(queryset)


    #---------------------------------------------------------------------------------------------------
    # Returns the list of heuristic versions to display, according to the mode and the configuration
    #---------------------------------------------------------------------------------------------------
    def _getHeuristicVersionsList(self):

        # Compute the sort key
        if not(self.configuration.sort_key in SORT_KEYS_VERSIONS):
            self.configuration.sort_key = 'v'
        actual_sort_key = SORT_KEYS_VERSIONS[self.configuration.sort_key]
        if self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        # Retrieve the heuristic versions from the database
        queryset = HeuristicVersion.objects.filter(heuristic=self.configuration.heuristic).exclude(status=HeuristicVersion.STATUS_DELETED)
        queryset = queryset.exclude(pk=self.configuration.heuristic_version.id)

        if self.mode.modify_queryset is not None:
            queryset = self.mode.modify_queryset(queryset, self.configuration)

        if self.configuration.sort_key == 'r':
            queryset = queryset.extra(select={'null_rank': 'heuristics_heuristicversion.rank is null'})
            queryset = queryset.extra(order_by=['null_rank', actual_sort_key])
        elif self.configuration.sort_key == 'd':
            secondary_sort_key = SORT_KEYS_VERSIONS['r']
            if self.configuration.sort_ordering == 'd':
                secondary_sort_key = '-' + secondary_sort_key

            queryset = queryset.extra(select={'null_rank': 'heuristics_heuristicversion.rank is null'})
            queryset = queryset.extra(order_by=[actual_sort_key, 'null_rank', secondary_sort_key])
        else:
            queryset = queryset.order_by(actual_sort_key)

        return self._setupPages(queryset)


    #---------------------------------------------------------------------------------------------------
    # Returns the list of derived heuristics to display, according to the mode and the configuration
    #---------------------------------------------------------------------------------------------------
    def _getDerivedHeuristicsList(self):

        manual_sort_key = None

        def _getLatestVisibleVersion(x):
            if x.latest_public_version is not None:
                return x.latest_public_version
            else:
                return x.latest_version()

        def _getFieldValue(version, fields):
            var = version
            for field in fields:
                if hasattr(var, field):
                    var = getattr(var, field)
                else:
                    break
            
            return var

        def _compareVersions(x, y):
            val1 = _getFieldValue(x, manual_sort_key)
            val2 = _getFieldValue(y, manual_sort_key)

            if self.configuration.sort_ordering == 'd':
                return -cmp(val1, val2)
            else:
                return cmp(val1, val2)


        # Compute the sort key
        actual_sort_key = SORT_KEYS[self.configuration.sort_key]
        if actual_sort_key.startswith('%s'):
            if self.mode.sort_key_prefix is not None:
                actual_sort_key = actual_sort_key % self.mode.sort_key_prefix
            else:
                manual_sort_key = actual_sort_key.replace('%s__', '').split('__')
                actual_sort_key = None
        elif self.configuration.sort_ordering == 'd':
            actual_sort_key = '-' + actual_sort_key

        secondary_sort_key = None
        if self.configuration.sort_key == 'u':
            secondary_sort_key = 'name'

        # Retrieve the derived heuristic from the database
        queryset = self.configuration.heuristic.derived_heuristics

        if self.configuration.query is not None:
            queryset = queryset.filter(Q(author__username__search=self.configuration.query) |
                                       Q(name__search=self.configuration.query) |
                                       Q(description__search=self.configuration.query) |
                                       Q(author__username__icontains=self.configuration.query) |
                                       Q(name__icontains=self.configuration.query) |
                                       Q(description__icontains=self.configuration.query))

        if self.configuration.initial is not None:
            queryset = queryset.filter(name__istartswith=self.configuration.initial)

        if self.mode.modify_queryset is not None:
            queryset = self.mode.modify_queryset(queryset, self.configuration)

        if secondary_sort_key:
            queryset = queryset.order_by(secondary_sort_key)

        if actual_sort_key is not None:
            heuristics = queryset.order_by(actual_sort_key)
        else:
            versions = map(_getLatestVisibleVersion, queryset.iterator())
            versions.sort(cmp=_compareVersions)
            heuristics = map(lambda x: x.heuristic, versions)
        
        return self._setupPages(heuristics=heuristics)


    def _setupPages(self, queryset=None, heuristics=None):

        if queryset is not None:
            nb_items = queryset.count()
            items = queryset[self.configuration.start:self.configuration.start+NB_HEURISTICS_PER_PAGE]
        else:
            nb_items = len(heuristics)
            items = heuristics[self.configuration.start:self.configuration.start+NB_HEURISTICS_PER_PAGE]

        # Compute the current page and their count
        if self.configuration.start >= nb_items:
            self.configuration.start = (nb_items / NB_HEURISTICS_PER_PAGE) * NB_HEURISTICS_PER_PAGE

        current_page = (self.configuration.start / NB_HEURISTICS_PER_PAGE) + 1
        nb_pages = int(math.ceil(float(nb_items) / NB_HEURISTICS_PER_PAGE))

        # Return the results
        return (items, nb_items, current_page, nb_pages)


    #---------------------------------------------------------------------------------------------------
    # Returns the HTML code of the header of the table containing the list
    #---------------------------------------------------------------------------------------------------
    def _getHTMLTableHeader(self):
        html = '<tr>\n'

        for entry in self.mode.header_entries:
            if (entry.condition is not None) and not(getattr(self.configuration, entry.condition)):
                continue
            
            if entry.sort_key is None:
                html += '<th>%s</th>\n' % entry.label
            elif (entry.sort_key == self.configuration.sort_key) and (self.configuration.sort_ordering == 'a'):
                html += '<th><a href="%s&%ssk=%s&%sso=d">%s</a></th>\n' % (self.configuration.headerUrl(), self.configuration.url_args_prefix, entry.sort_key, self.configuration.url_args_prefix, entry.label)
            else:
                html += '<th><a href="%s&%ssk=%s">%s</a></th>\n' % (self.configuration.headerUrl(), self.configuration.url_args_prefix, entry.sort_key, entry.label)

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
                    html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str(i * NB_HEURISTICS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        elif current_page < PAGES_NAVIGATION_PREV_NEXT_COUNT:
            for i in range(0, PAGES_NAVIGATION_BORDER_COUNT):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str(i * NB_HEURISTICS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

            if nb_pages > PAGES_NAVIGATION_BORDER_COUNT + 1:
                html += '...'

            html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str((nb_pages - 1) * NB_HEURISTICS_PER_PAGE) }) + '">' + str(nb_pages) + '</a>'

        elif current_page <= PAGES_NAVIGATION_BORDER_COUNT:
            max = current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT
            if max > nb_pages:
                max = nb_pages

            for i in range(0, max):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str(i * NB_HEURISTICS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

            if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT:
                if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
                    html += '...'

                html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str((nb_pages - 1) * NB_HEURISTICS_PER_PAGE) }) + '">' + str(nb_pages) + '</a>'

        elif current_page > nb_pages - PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
            if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 0:
                html += '<a href="' + url + '&' + self.configuration.url_args_prefix + 's=0">1</a>'

                if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 1:
                    html += '...'

            for i in range(nb_pages - PAGES_NAVIGATION_BORDER_COUNT, nb_pages):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str(i * NB_HEURISTICS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        elif current_page > nb_pages - PAGES_NAVIGATION_BORDER_COUNT:
            if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 0:
                html += '<a href="' + url + '&' + self.configuration.url_args_prefix + 's=0">1</a>'

                if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 1:
                    html += '...'

            for i in range(current_page - PAGES_NAVIGATION_PREV_NEXT_COUNT - 1, nb_pages):
                if i == current_page - 1:
                    html += '<strong>' + str(i+1) + '</strong>'
                else:
                    html += '<a href="' + self.configuration._buildUrl(url, { self.configuration.url_args_prefix + 's': str(i * NB_HEURISTICS_PER_PAGE) }) + '">' + str(i+1) + '</a>'

        html += '</span>'

        return html


#---------------------------------------------------------------------------------------------------
# Returns the HTML code representing the source code of a specific heuristic version
#---------------------------------------------------------------------------------------------------
def get_source_code_as_html(version):

    source = get_source_code(version)

    # Format the source code of the heuristic
    lexer = CppLexer(tabsize=4)
    formatter = HtmlFormatter(linenos='table', cssclass="sourcecode", anchorlinenos=True,
                              lineanchors='line')
    return '<div class="code">' + highlight(source.data, lexer, formatter) + '</div>'


def get_source_code(version):
    # Retrieve the repository and lock it
    if version.checked:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
    else:
        repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
    
    repo.createIfNotExists()
    repo.lock()

    try:
        # Retrieve the source code file from the repository
        blob = repo.repository().tree()[version.heuristic.author.username.lower()][version.filename]

        # Release the lock
        repo.unlock()

    except:
        repo.unlock()
        # Just in case
        try:
            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
            repo.createIfNotExists()
            repo.lock()
            
            blob = repo.repository().tree()[version.heuristic.author.username.lower()][version.filename]

            repo.unlock()
        except:
            repo.unlock()
            raise
    
    return blob

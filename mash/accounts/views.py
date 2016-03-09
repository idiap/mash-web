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


﻿from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import connection, transaction
from django.views.decorators.cache import never_cache
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import Site, RequestSite
from accounts.models import UserProfile
from phpbb.models import PhpbbUser, PhpbbGroup, PhpbbUserGroup, PhpbbUserRank
from wiki.models import WikiUser
from tools.models import PluginErrorReport
from tools.views import get_error_report_as_html
from django.utils import simplejson
from django.template import defaultfilters
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.utilities import *
from pymash.gitrepository import GitRepository
import os
import shutil


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

NB_USERS_PER_PAGE                   = 50
PAGES_NAVIGATION_BORDER_COUNT       = 5
PAGES_NAVIGATION_PREV_NEXT_COUNT    = 3

INITIALS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

SORT_KEYS = { 'i': 'user__id', 'u': 'user__username', 'r': 'forum_user__user_rank', 'm': 'user__email', 'h': 'heuristics_count',
              'p': 'posts_count', 'w': 'forum_user__user_website', 'l': 'forum_user__user_from', 'd': 'user__date_joined'}



####################################################################################################
#
# HTML GENERATION FUNCTIONS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Used to build a list of arguments (?arg1=val1&arg2=val2...)
#---------------------------------------------------------------------------------------------------
def get_argument(name, value, first_arg):
    if value:
        if first_arg:
            return '?' + name + '=' + str(value)
        else:
            return '&' + name + '=' + str(value)

    return ''



#---------------------------------------------------------------------------------------------------
# Returns the HTML code of the pages navigation control on the members list page
#---------------------------------------------------------------------------------------------------
def build_pages_navigation(current_page, nb_pages, url):
    html = '<span id="pages_nav">'

    if nb_pages <= PAGES_NAVIGATION_BORDER_COUNT:
        for i in range(0, nb_pages):
            if i == current_page - 1:
                html += '<strong>' + str(i+1) + '</strong>'
            else:
                html += '<a href="' + url + '&s=' + str(i * NB_USERS_PER_PAGE) + '">' + str(i+1) + '</a>'

    elif current_page < PAGES_NAVIGATION_PREV_NEXT_COUNT:
        for i in range(0, PAGES_NAVIGATION_BORDER_COUNT):
            if i == current_page - 1:
                html += '<strong>' + str(i+1) + '</strong>'
            else:
                html += '<a href="' + url + '&s=' + str(i * NB_USERS_PER_PAGE) + '">' + str(i+1) + '</a>'

        if nb_pages > PAGES_NAVIGATION_BORDER_COUNT + 1:
            html += '...'

        html += '<a href="' + url + '&s=' + str((nb_pages - 1) * NB_USERS_PER_PAGE) + '">' + str(nb_pages) + '</a>'

    elif current_page <= PAGES_NAVIGATION_BORDER_COUNT:
        max = current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT
        if max > nb_pages:
            max = nb_pages

        for i in range(0, max):
            if i == current_page - 1:
                html += '<strong>' + str(i+1) + '</strong>'
            else:
                html += '<a href="' + url + '&s=' + str(i * NB_USERS_PER_PAGE) + '">' + str(i+1) + '</a>'

        if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT:
            if nb_pages > current_page + PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
                html += '...'

            html += '<a href="' + url + '&s=' + str((nb_pages - 1) * NB_USERS_PER_PAGE) + '">' + str(nb_pages) + '</a>'

    elif current_page > nb_pages - PAGES_NAVIGATION_PREV_NEXT_COUNT + 1:
        if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 0:
            html += '<a href="' + url + '&s=0">1</a>'

            if nb_pages - PAGES_NAVIGATION_BORDER_COUNT > 1:
                html += '...'

        for i in range(nb_pages - PAGES_NAVIGATION_BORDER_COUNT, nb_pages):
            if i == current_page - 1:
                html += '<strong>' + str(i+1) + '</strong>'
            else:
                html += '<a href="' + url + '&s=' + str(i * NB_USERS_PER_PAGE) + '">' + str(i+1) + '</a>'

    elif current_page > nb_pages - PAGES_NAVIGATION_BORDER_COUNT:
        if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 0:
            html += '<a href="' + url + '&s=0">1</a>'

            if current_page - PAGES_NAVIGATION_BORDER_COUNT - 1 > 1:
                html += '...'

        for i in range(current_page - PAGES_NAVIGATION_PREV_NEXT_COUNT - 1, nb_pages):
            if i == current_page - 1:
                html += '<strong>' + str(i+1) + '</strong>'
            else:
                html += '<a href="' + url + '&s=' + str(i * NB_USERS_PER_PAGE) + '">' + str(i+1) + '</a>'

    html += '</span>'

    return html



#---------------------------------------------------------------------------------------------------
# Returns the HTML code of a link used to sort the members list
#---------------------------------------------------------------------------------------------------
def build_members_list_header_link(url, sort_key, current_sort_key, sort_ordering, label):
    html = '<a href="' + url + '&sk=' + sort_key

    if (current_sort_key == sort_key) and (sort_ordering == 'a'):
        html += '&so=d'

    html += '">' + label + '</a>'

    return html



#---------------------------------------------------------------------------------------------------
# Returns the HTML code of the header of the table containing the members list
#---------------------------------------------------------------------------------------------------
def build_members_list_header(url, sort_key, sort_ordering, admin, select_column=False):

    html = '<thead>\n<tr>\n'

    if select_column:
        html += '<th colspan="2">'
    else:
        html += '<th>'

    html += build_members_list_header_link(url, 'u', sort_key, sort_ordering, 'USERNAME') + '</th>\n'

    if admin:
        html += '<th>' + build_members_list_header_link(url, 'm', sort_key, sort_ordering, 'E-MAIL') + '</th>\n'

    html += '<th>' + build_members_list_header_link(url, 'r', sort_key, sort_ordering, 'GROUP') + '</th>\n'
    html += '<th>' + build_members_list_header_link(url, 'h', sort_key, sort_ordering, 'HEURISTICS') + '</th>\n'
    html += '<th>' + build_members_list_header_link(url, 'p', sort_key, sort_ordering, 'POSTS') + '</th>\n'
    html += '<th>' + build_members_list_header_link(url, 'w', sort_key, sort_ordering, 'WEBSITE') + \
            ', ' + build_members_list_header_link(url, 'l', sort_key, sort_ordering, 'LOCATION') + '</th>\n'
    html += '<th>' + build_members_list_header_link(url, 'd', sort_key, sort_ordering, 'JOINED') + '</th>\n'

    html += '</tr>\n</thead>\n'

    return html



####################################################################################################
#
# VIEWS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Allows a user to log in. This is a modified version of the 'django.contrib.auth.views.login'
# function, that check that cookies are enabled
#---------------------------------------------------------------------------------------------------
@never_cache
def login(request, template_name='accounts/login.html', redirect_field_name=REDIRECT_FIELD_NAME):
    "Displays the login form and handles the login action."
    redirect_to = request.REQUEST.get(redirect_field_name, '')

    test_cookie_worked = True

    if request.method == "POST":

        form = AuthenticationForm(data=request.POST)
        test_cookie_worked = request.session.test_cookie_worked()
        if test_cookie_worked:
            request.session.delete_test_cookie()

        if form.is_valid() and test_cookie_worked:
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL

            #ready to login so check if cookie exist
            userUsername = request.POST.__getitem__('username')
            anonuser_db=''
            cookie_value = ""
            if request.COOKIES.has_key('robot_uid'):
                cookie_value = request.COOKIES.__getitem__('robot_uid')
                #user is anonymous
                anonUser = "anon_%s"%cookie_value
                #check if anonymous user has already used the system
                try :
                    User.objects.all().get(username=anonUser)
                    anonuser_db = User.objects.all().get(username=anonUser)
                    user_db = User.objects.all().get(username=userUsername)
                    #only display simple heuristics from current user
                    heuristiclist = HeuristicVersion.objects.filter(heuristic__simple=True).filter(heuristic__author__id=anonuser_db.id)
                    heuristicUserlist = HeuristicVersion.objects.filter(heuristic__simple=True).filter(heuristic__author__id=user_db.id)

                    #check if heuristicname already exist
                    for simpleHeuristicAnon in heuristiclist:
                        versionAnon = get_object_or_404(HeuristicVersion, pk=simpleHeuristicAnon.id)
                        heuristicAnon = get_object_or_404(Heuristic, pk=simpleHeuristicAnon.heuristic_id)

                        nameCounter = 1
                        finalName = '%s'%heuristicAnon.name
                        while (Heuristic.objects.filter(author__id=user_db.id).filter(name='%s'%finalName).count() > 0):
                            nameCounter += 1
                            finalName = '%s%d' % (heuristicAnon.name, nameCounter)
                        newHeuristicAnonFilename = '%s.cpp' % (finalName)
                        # Retrieve the repository containing the source file and lock it
                        if versionAnon.checked:
                            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                        else:
                            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
                        repo.lock()

                        try:
                            # move repository folder from anonymous to newly registered user
                            repo.moveFile('%s/%s.cpp*' % (anonUser, heuristicAnon.name), '%s/%s' % (anonUser, newHeuristicAnonFilename),
                            "Simple Heuristic '%s' modified name (by %s)" % (newHeuristicAnonFilename, anonuser_db.username),
                            settings.COMMIT_AUTHOR)
                        except:
                            pass

                        # Release the lock
                        repo.unlock()

                        #update Databse with new name and filename
                        versionAnon.filename = newHeuristicAnonFilename
                        heuristicAnon.name = finalName
                        versionAnon.save()
                        heuristicAnon.save()


                    #modify author_id
                    for simpleHeuristic in heuristiclist:
                        version = get_object_or_404(HeuristicVersion, pk=simpleHeuristic.id)
                        heuristic = get_object_or_404(Heuristic, pk=simpleHeuristic.heuristic_id)
                        heuristic.author = user_db
                        heuristic.save()

                        # Retrieve the repository containing the source file and lock it
                        if version.checked:
                            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                        else:
                            repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
                        repo.lock()

                        try:
                            # move repository folder from anonymous to newly registered user
                            repo.moveFile('%s/*' % (anonUser), '%s/' % (user_db.username.lower()),
                            "Simple Heuristic '%s' moved to logged user (by %s)" % (heuristiclist, user_db.username),
                            settings.COMMIT_AUTHOR)
                            anondirToRemove = "%s/%s"%(repo.fullpath(),anonUser)
                            os.removedirs("%s"%anondirToRemove)
                        except:
                            pass

                        # Release the lock
                        repo.unlock()
                    ##delete anonymous user from database
                    anonuser_db.delete()


                except User.DoesNotExist :
                    #Not found anonymous user
                    pass
                #anonymous user is refered by anon_<cookievalue>
            else :
                #no cookie
                pass


            from django.contrib.auth import login
            login(request, form.get_user())

            return HttpResponseRedirect(redirect_to)
    else:
        form = AuthenticationForm(request)

    request.session.set_test_cookie()

    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)

    return render_to_response(template_name,
                              { 'form': form,
                                redirect_field_name: redirect_to,
                                'site_name': current_site.name,
                                'test_cookie_worked': test_cookie_worked, },
                              context_instance=RequestContext(request))



#---------------------------------------------------------------------------------------------------
# Display the profile of an user
#---------------------------------------------------------------------------------------------------
def profile(request, user_id=None):

    # Retrieve the user to display
    if user_id is not None:
        target_user = get_object_or_404(User, pk=user_id)
    else:
        target_user = request.user

    # Account creation-related stuff for non-anonymous users
    if not(request.user.is_anonymous()):
        # Check that the account of the user viewing the page was activated, or is a superuser one
        if not(request.user.is_active):
            if request.user.is_superuser:
                request.user.is_active = True
                request.user.save()
            else:
                raise Http404

        profile = request.user.get_profile()

        # Check that the user has a forum account. This is done here because the users are redirected
        # here after a successfull login. If the user don't have a forum account yet, one is created by
        # redirecting him to the forum URL doing that, and then redirecting him here. Not that good, but
        # it is the only way to reuse the forum's code to create the account.

        forum_user = profile.forum_user
        if forum_user is None:
            try:
                forum_user = PhpbbUser.objects.get(username=request.user.username)
                profile.forum_user = forum_user
                profile.save()
            except:
                if settings.HTTPS_SUPPORT:
                    return HttpResponseRedirect(settings.SECURED_FORUM_URL_DOMAIN + '/forum/ucp.php?mode=login&redirect=' +
                                                settings.SECURED_WEBSITE_URL_DOMAIN + '/accounts/profile/' + str(target_user.id))
                else:
                    return HttpResponseRedirect(settings.FORUM_URL_DOMAIN + '/forum/ucp.php?mode=login&redirect=' +
                                                settings.WEBSITE_URL_DOMAIN + '/accounts/profile/' + str(target_user.id))

        # Check that the user has a wiki account
        if profile.wiki_user is None:
            try:
                profile.wiki_user = WikiUser.objects.get(user_name=request.user.username)
                profile.save()

                if len(profile.wiki_user.user_email) == 0:
                    profile.wiki_user.user_email = request.user.email
                    profile.wiki_user.save()
            except:
                pass

    if target_user.is_anonymous():
        raise Http404


    # Display the error reports concerning this user
    html_heuristic_error_reports    = None
    html_classifier_error_reports   = None
    html_goalplanner_error_reports  = None
    html_instrument_error_reports   = None
    groups                          = None

    if target_user == request.user:
        reports = PluginErrorReport.objects.filter(heuristic_version__isnull=False) \
                                           .filter(heuristic_version__heuristic__author=target_user)
        for report in reports:
            if (report.heuristic_version.public and (report.heuristic_version.heuristic.latest_public_version != report.heuristic_version)) or \
               (not(report.heuristic_version.public) and (report.heuristic_version.heuristic.latest_private_version != report.heuristic_version)):
                continue

            if html_heuristic_error_reports is None:
                html_heuristic_error_reports = ''

            html_heuristic_error_reports += get_error_report_as_html(report, request.user, display_title=True,
                                                                     title_class='blue',
                                                                     title_link='/heuristics/v%d' % report.heuristic_version.id,
                                                                     display_experiment=True)

        reports = PluginErrorReport.objects.filter(classifier__isnull=False).filter(classifier__author=target_user)
        for report in reports:
            if html_classifier_error_reports is None:
                html_classifier_error_reports = ''

            html_classifier_error_reports += get_error_report_as_html(report, request.user, display_title=True,
                                                                      title_class='blue', display_experiment=True)

        reports = PluginErrorReport.objects.filter(goalplanner__isnull=False).filter(goalplanner__author=target_user)
        for report in reports:
            if html_goalplanner_error_reports is None:
                html_goalplanner_error_reports = ''

            html_goalplanner_error_reports += get_error_report_as_html(report, request.user, display_title=True,
                                                                       title_class='blue', display_experiment=True)

        reports = PluginErrorReport.objects.filter(instrument__isnull=False).filter(instrument__author=target_user)
        for report in reports:
            if html_instrument_error_reports is None:
                html_instrument_error_reports = ''

            html_instrument_error_reports += get_error_report_as_html(report, request.user, display_title=True,
                                                                      title_class='blue', display_experiment=True)

        groups = target_user.get_profile().leaded_groups()


    # Render the page
    return render_to_response('accounts/profile.html',
                              {'target_user': target_user,
                               'profile': target_user.get_profile(),
                               'groups': groups,
                               'html_heuristic_error_reports': html_heuristic_error_reports,
                               'html_classifier_error_reports': html_classifier_error_reports,
                               'html_goalplanner_error_reports': html_goalplanner_error_reports,
                               'html_instrument_error_reports': html_instrument_error_reports,
                              },
                              context_instance=RequestContext(request))



#---------------------------------------------------------------------------------------------------
# Display the profile of an user, from its forum user ID
#---------------------------------------------------------------------------------------------------
def forum_profile(request, user_id=None):

    target_forum_user = get_object_or_404(PhpbbUser, pk=user_id)
    target_user = get_object_or_404(User, username=target_forum_user.username)

    return render_to_response('accounts/profile.html',
                              {'target_user': target_user,
                               'profile': target_user.get_profile(),
                              },
                              context_instance=RequestContext(request))



#---------------------------------------------------------------------------------------------------
# Display the list of the members (eventually sorted and filtered)
#---------------------------------------------------------------------------------------------------
def members(request, search_popup=False):

    # Default values for the arguments
    initial         = None
    group           = None
    query           = None
    sort_key        = 'i'
    sort_ordering   = 'a'
    start           = 0
    search_form     = None
    search_field    = None
    search_single   = False


    # Retrieve and validate the arguments
    if request.GET.has_key('i'):
        initial = request.GET['i']
        if len(initial) != 1:
            initial = None

    if request.GET.has_key('g'):
        try:
            group = int(request.GET['g'])
        except:
            pass

    if request.POST.has_key('query'):
        query = request.POST['query']
        if query in [ u'Search\u2026', u'Search...', 'Search...' ]:
            query = None

    if (query is None) and request.GET.has_key('q'):
        query = request.GET['q']

    if request.GET.has_key('sk'):
        sort_key = request.GET['sk']
        if (len(sort_key) != 1) or not(SORT_KEYS.has_key(sort_key)):
            sort_key = 'i'

    if request.GET.has_key('so'):
        sort_ordering = request.GET['so']
        if (sort_ordering != 'a') and (sort_ordering != 'd'):
            sort_ordering = 'a'

    if request.GET.has_key('s'):
        try:
            start = int(request.GET['s'])
            start = (start / NB_USERS_PER_PAGE) * NB_USERS_PER_PAGE
        except:
            pass

    if search_popup:
        if request.GET.has_key('form'):
            search_form = request.GET['form']

        if request.GET.has_key('field'):
            search_field = request.GET['field']

        if request.GET.has_key('select_single'):
            try:
                val = request.GET['select_single'].lower()
                search_single = (val == 'true') or (val == u'true') or (int(val) == 1)
            except:
                pass

        if (search_form is None) or (search_field is None) or (len(search_form) == 0) or (len(search_field) == 0):
            search_popup = False


    # Compute the variables needed to create the URLs of the links of the page
    args = get_argument('g', group, True)

    if search_popup:
        args += get_argument('form', search_form, len(args) == 0)
        args += get_argument('field', search_field, len(args) == 0)

        if search_single:
            args += get_argument('select_single', '1', len(args) == 0)
        else:
            args += get_argument('select_single', '0', len(args) == 0)

    args_with_query = args + get_argument('q', query, len(args) == 0)
    args_with_initial = args_with_query + get_argument('i', initial, len(args_with_query) == 0)

    args_sorting = 'sk=' + sort_key + '&so=' + sort_ordering

    args_prefix = '&'
    if len(args) == 0:
        args_prefix = '?'

    args_with_query_prefix = '&'
    if len(args_with_query) == 0:
        args_with_query_prefix = '?'

    args_with_initial_prefix = '&'
    if len(args_with_initial) == 0:
        args_with_initial_prefix = '?'


    # Compute the sort key
    actual_sort_key = SORT_KEYS[sort_key]
    if sort_ordering == 'd':
        actual_sort_key = '-' + actual_sort_key


    # Retrieve the users from the database
    # NOTE: The call to extra() here should be replaced by a call to aggregate() when using Django >= 1.1
    queryset = UserProfile.objects.extra(select={
        'heuristics_count': 'SELECT COUNT(*) FROM heuristics_heuristic WHERE heuristics_heuristic.author_id = accounts_userprofile.user_id AND heuristics_heuristic.latest_public_version_id IS NOT NULL',
        'posts_count': 'SELECT COUNT(*) FROM phpbb_posts WHERE phpbb_posts.poster_id = accounts_userprofile.forum_user_id',
    })

    queryset = queryset.filter(user__is_active=True)

    if query is not None:
        queryset = queryset.filter(Q(user__username__search=query) | Q(user__first_name__search=query) |
                                   Q(user__last_name__search=query) | Q(user__email__search=query) |
                                   Q(forum_user__user_occupation__search=query) | Q(forum_user__user_from__search=query) |
                                   Q(forum_user__user_website__search=query) | Q(forum_user__user_interests__search=query) |
                                   Q(user__username__icontains=query) | Q(user__first_name__icontains=query) |
                                   Q(user__last_name__icontains=query) | Q(user__email__icontains=query) |
                                   Q(forum_user__user_occupation__icontains=query) | Q(forum_user__user_from__icontains=query) |
                                   Q(forum_user__user_website__icontains=query) | Q(forum_user__user_interests__icontains=query))

    if initial == '_':
        queryset = queryset.filter(user__username__iregex=r'^[^a-z]')
    elif initial is not None:
        queryset = queryset.filter(user__username__istartswith=initial)

    if group is not None:
        queryset = queryset.filter(forum_user__phpbbusergroup__group__group_id=group)

    user_profiles = queryset.order_by(actual_sort_key)

    nb_users = user_profiles.count()

    user_profiles = user_profiles[start:start+NB_USERS_PER_PAGE]


    # Retrieve the group name (if necessary)
    group_name = None
    if group is not None:
        group_name = PhpbbGroup.objects.get(pk=group).display_name()


    # Compute the current page and their count
    if start >= nb_users:
        start = (nb_users / NB_USERS_PER_PAGE) * NB_USERS_PER_PAGE

    current_page = (start / NB_USERS_PER_PAGE) + 1
    nb_pages = (nb_users / NB_USERS_PER_PAGE) + 1


    # Render the page
    return render_to_response('accounts/members.html',
                              {'letters': INITIALS,
                               'current_page': current_page,
                               'nb_pages': nb_pages,
                               'page_url': request.path + args_with_initial + args_with_initial_prefix + args_sorting,
                               'page_url_without_query': request.path + args + args_prefix + args_sorting,
                               'page_url_without_initial': request.path + args_with_query + args_with_query_prefix + args_sorting,
                               'pages_navigation': build_pages_navigation(current_page, nb_pages, request.path + args_with_query + args_with_query_prefix + args_sorting),
                               'nb_users': nb_users,
                               'nb_users_per_page': NB_USERS_PER_PAGE,
                               'group_name': group_name,
                               'table_header': build_members_list_header(request.path + args_with_initial + args_with_initial_prefix + 's=' + str(start),
                                                                         sort_key, sort_ordering, not(request.user.is_anonymous()) and request.user.get_profile().project_member,
                                                                         select_column=(search_popup and not(search_single))),
                               'user_profiles': user_profiles,
                               'query': query,
                               'search_popup': search_popup,
                               'search_form': search_form,
                               'search_field': search_field,
                               'search_single': search_single,
                               },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Create a new group of users, leaded by the current one
#---------------------------------------------------------------------------------------------------
@login_required
def group_create(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    try:
        group_name = request.POST['name']
    except:
        raise Http404


    response_content = {
        'error': False,
        'name': None,
        'id': None,
    }

    if group_name.lower().startswith(request.user.username.lower() + '/'):
        group_name = request.user.username + group_name[len(request.user.username):]
    else:
        group_name = request.user.username + '/' + group_name

    response_content['name'] = group_name

    group = None
    try:
        group = PhpbbGroup.objects.get(group_name__iexact=group_name)
        response_content['error'] = True
    except:
        pass

    if group is None:
        group            = PhpbbGroup()
        group.group_type = PhpbbGroup.GROUP_TYPE_HIDDEN
        group.group_name = group_name
        group.save()

        # Must retrieve 'group' from the DB, for some reason 'group.group_id' isn't updated
        group = PhpbbGroup.objects.get(group_name__iexact=group_name)

        response_content['id'] = group.group_id

        user_group_link                 = PhpbbUserGroup()
        user_group_link.group           = group
        user_group_link.user            = request.user.get_profile().forum_user
        user_group_link.group_leader    = 1
        user_group_link.user_pending    = 0
        user_group_link.save()

    response = HttpResponse(mimetype="text/plain")

    # Prevent ajax cache in IE8
    response["Cache-Control"] = "max-age=0,no-cache,no-store"

    response.write(simplejson.dumps(response_content))

    return response


#---------------------------------------------------------------------------------------------------
# Delete a group of users
#---------------------------------------------------------------------------------------------------
@login_required
def group_delete(request):

    # Only by Ajax
    if not(request.is_ajax()):
        raise Http404

    try:
        group_id = int(request.POST['id'])
    except:
        raise Http404

    from django.db import connection, transaction
    cursor = connection.cursor()
    cursor.execute("DELETE FROM %suser_group WHERE group_id=%d" % (settings.DATABASE_PHPBB_PREFIX, group_id))
    transaction.commit_unless_managed()

    cursor.execute("DELETE FROM %sgroups WHERE group_id=%d" % (settings.DATABASE_PHPBB_PREFIX, group_id))
    transaction.commit_unless_managed()

    response = HttpResponse(mimetype="text/plain")

    # Prevent ajax cache in IE8
    response["Cache-Control"] = "max-age=0,no-cache,no-store"

    response.write('OK')

    return response


def add_user_to_forum_group(user, group):
    profile = user.get_profile()

    if profile.forum_user is not None:
        link = PhpbbUserGroup.objects.filter(user__user_id=profile.forum_user.user_id).filter(group__group_name=group)
        if link.count() == 0:
            link = PhpbbUserGroup()
            link.user = profile.forum_user
            link.group = PhpbbGroup.objects.get(group_name=group)
            link.group_leader = 0
            link.user_pending = 0
            link.save()


def remove_user_from_forum_group(user, group):
    profile = user.get_profile()

    if profile.forum_user is not None:
        link = PhpbbUserGroup.objects.filter(user__user_id=profile.forum_user.user_id).filter(group__group_name=group)
        if link.count() == 1:
            group = PhpbbGroup.objects.get(group_name=group)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM phpbb_user_group WHERE group_id=%s AND user_id=%s", [group.group_id, profile.forum_user.user_id])
            transaction.commit_unless_managed()


def set_user_rank_for_contributor(user):
    profile = user.get_profile()

    if profile.forum_user is not None:
        ranks = PhpbbUserRank.objects.filter(rank_special=0).filter(rank_min__lte=profile.forum_user.user_posts).order_by('-rank_min')
        if ranks.count() > 0:
            profile.forum_user.user_rank = ranks[0]
            profile.forum_user.save()
        else:
            set_user_rank(user, 'Contributor')


def set_user_rank(user, rank_title):
    profile = user.get_profile()

    if profile.forum_user is not None:
        ranks = PhpbbUserRank.objects.filter(rank_title=rank_title)
        if ranks.count() == 1:
            profile.forum_user.user_rank = ranks[0]
            profile.forum_user.save()
        else:
            set_user_rank_for_contributor(user)


#---------------------------------------------------------------------------------------------------
# Promote an user to 'superuser'
#---------------------------------------------------------------------------------------------------
@login_required
def promote_to_superuser(request, user_id):

    # Check that the current user has the right to do that
    if not(request.user.is_superuser):
        raise Http404

    # Promote the user
    target_user = get_object_or_404(User, pk=user_id)
    target_user.is_superuser = True
    target_user.is_staff = True
    target_user.save()

    profile = target_user.get_profile()
    profile.project_member = True
    profile.save()

    add_user_to_forum_group(target_user, 'ADMINISTRATORS')
    add_user_to_forum_group(target_user, 'GLOBAL_MODERATORS')
    add_user_to_forum_group(target_user, 'Project members')

    set_user_rank(target_user, 'Core team')

    # Redirect to the user's profile page
    return HttpResponseRedirect('/accounts/profile/%s/' % user_id)


#---------------------------------------------------------------------------------------------------
# Promote an user to 'project member'
#---------------------------------------------------------------------------------------------------
@login_required
def promote_to_projectmember(request, user_id):

    # Check that the current user has the right to do that
    if not(request.user.is_superuser):
        raise Http404

    # Promote the user
    target_user = get_object_or_404(User, pk=user_id)
    target_user.is_superuser = False
    target_user.is_staff = True
    target_user.save()

    profile = target_user.get_profile()
    profile.project_member = True
    profile.save()

    remove_user_from_forum_group(target_user, 'ADMINISTRATORS')
    add_user_to_forum_group(target_user, 'GLOBAL_MODERATORS')
    add_user_to_forum_group(target_user, 'Project members')

    set_user_rank(target_user, 'Core team')

    # Redirect to the user's profile page
    return HttpResponseRedirect('/accounts/profile/%s/' % user_id)


#---------------------------------------------------------------------------------------------------
# Promote an user to 'contributor'
#---------------------------------------------------------------------------------------------------
@login_required
def promote_to_contributor(request, user_id):

    # Check that the current user has the right to do that
    if not(request.user.is_superuser):
        raise Http404

    # Promote the user
    target_user = get_object_or_404(User, pk=user_id)
    target_user.is_superuser = False
    target_user.is_staff = False
    target_user.save()

    profile = target_user.get_profile()
    profile.project_member = False
    profile.save()

    remove_user_from_forum_group(target_user, 'ADMINISTRATORS')
    remove_user_from_forum_group(target_user, 'GLOBAL_MODERATORS')
    remove_user_from_forum_group(target_user, 'Project members')

    set_user_rank_for_contributor(target_user)

    # Redirect to the user's profile page
    return HttpResponseRedirect('/accounts/profile/%s/' % user_id)

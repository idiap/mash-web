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


from menu.models import MenuItem
from phpbb.models import PhpbbPrivateMessageInfos
from accounts.models import UserProfile
from django.conf import settings
from django import template


register = template.Library()


####################################################################################################
#
#                           Implementation of the 'menu' tag
#
####################################################################################################


def build_menu(parser, token):
    """
    {% menu %}
    """
    return MenuObject()


class MenuObject(template.Node):

    def render(self, context):
        try:
            current_path = template.Variable('request.path').resolve(context)
            authenticated = template.Variable('request.user').resolve(context).is_authenticated()
            admin = template.Variable('request.user').resolve(context).is_superuser
        except template.VariableDoesNotExist:
            current_path = ''
            authenticated = False
            admin = False
            
        result = '<ul>'
        
        items = list(MenuItem.objects.all())
        items.sort(cmp=lambda x,y: int(x.index - y.index))
        
        for item in items:
        
            if ((item.display == 'USER') or (item.display == 'ADMIN')) and not(authenticated):
                continue
        
            if (item.display == 'ANONYMOUS') and authenticated:
                continue

            if (item.display == 'ADMIN') and not(admin):
                continue

            if current_path.startswith(item.link + '/') or (item.link == '/' and current_path == '/'):
                result += '<li class="active">'
            else:
                result += '<li>'
                
            result += '<a href="' + item.link + '"><span>' + item.label + '</span></a></li>'
        
        result += '</ul>'

        return result


register.tag('menu', build_menu)



####################################################################################################
#
#                           Implementation of the 'login_infos' tag
#
####################################################################################################


def build_login_infos(parser, token):
    """
    {% login_infos %}
    """
    return LoginInfosObject()


class LoginInfosObject(template.Node):

    def render(self, context):
        try:
            user = template.Variable('request.user').resolve(context)
        
            if user.is_authenticated():
            
                try:
                    nb_pms = PhpbbPrivateMessageInfos.objects.filter(user__exact=user.get_profile().forum_user).filter(unread__exact=1).count()
                except UserProfile.DoesNotExist:
                    nb_pms = 0
            
                result = '<span>Logged in as <a id="username" href="/accounts/profile">' + user.username + '</a> | '

                if nb_pms > 0:
                    result += '<a id="inbox" class="not-empty" href="/forum/ucp.php?i=pm&folder=inbox">Inbox (%s)</a> | ' % str(nb_pms)
                else:
                    result += '<a id="inbox" class="empty" href="/forum/ucp.php?i=pm&folder=inbox">Inbox (0)</a> | '
            
                if user.is_staff:
                    result += '<a href="/admin">Admin</a> | '
            
                result += '<a class="last" href="/accounts/logout">Logout</a></span>'
            
                return result
        except template.VariableDoesNotExist:
            pass
        
        return '<span><a href="/accounts/login">Login</a> | <a class="last" href="/accounts/register">Register</a></span>'


register.tag('login_infos', build_login_infos)

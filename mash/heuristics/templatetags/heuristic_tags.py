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


from mash.heuristics.models import Heuristic, HeuristicVersion
from django import template
import re


register = template.Library()


####################################################################################################
#
#                           Implementation of the 'latest_heuristic_version' tag
#
####################################################################################################


class LatestHeuristicVersionNode(template.Node):
    
    def __init__(self, heuristic, user, var_name):
        self.heuristic = template.Variable(heuristic)
        self.user = template.Variable(user)
        self.var_name = var_name
    
    def render(self, context):
        heuristic = self.heuristic.resolve(context)
        user = self.user.resolve(context)
        
        if (heuristic.author == user) or (not(user.is_anonymous()) and user.get_profile().project_member):
            context[self.var_name] = heuristic.latest_version()
        else:
            context[self.var_name] = heuristic.latest_public_version
        return ''


def do_latest_heuristic_version(parser, token):

    try:
        tag_name, heuristic, user, as_word, var_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]
    
    if as_word != 'as':
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    return LatestHeuristicVersionNode(heuristic, user, var_name)


register.tag('latest_heuristic_version', do_latest_heuristic_version)

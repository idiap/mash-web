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


from django.shortcuts import render_to_response, get_object_or_404
from django.template import loader, RequestContext
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseServerError
from mash.news.views import get_latest_news
from mash.heuristics.models import Heuristic
from mash.texts_db.models import Text


NB_NEWS = 3


def index(request):

    # Retrieve the latest news
    latest_news_list = get_latest_news(NB_NEWS)

    text = Text.getMultilineContent('HOMEPAGE')

    return render_to_response('homepage/index.html',
                              { 'latest_news_list': latest_news_list,
                                'text': text,
                              },
                              context_instance=RequestContext(request))


def custom_error_view(request):
    template = loader.get_template('500.html')
    return HttpResponseServerError(template.render(RequestContext(request, {})))

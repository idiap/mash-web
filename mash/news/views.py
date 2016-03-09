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
from django.template import RequestContext, Context, loader
from mash.news.models import News


####################################################################################################
#
# CONSTANTS
#
####################################################################################################

NB_NEWS_BY_PAGE = 10



####################################################################################################
#
# HTML GENERATION FUNCTIONS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Return an html list of the latest news, that can be embedded in any page (be sure to import the
# news stylesheet, or to declare your own)
#---------------------------------------------------------------------------------------------------
def get_latest_news(nb_news):

    # Retrieve the latest news
    latest_news = News.objects.all().order_by('-pub_date')[0:nb_news]

    # Render the list
    template = loader.get_template('news/news_list_box.html')
    context = Context({'news_list': latest_news,
                       'details_enabled': False,
                      })
    return template.render(context)



####################################################################################################
#
# VIEWS
#
####################################################################################################

#---------------------------------------------------------------------------------------------------
# Display a list of news
#---------------------------------------------------------------------------------------------------
def index(request):
    nb_news = News.objects.count()
    
    first = 0
    if request.GET.has_key('first'):
        try:
            first = int(request.GET['first'])
        except ValueError:
            pass
    
    news_list = News.objects.all().order_by('-pub_date')[first:first + NB_NEWS_BY_PAGE]
    
    previous_index = False
    next_index = False
    
    if first + NB_NEWS_BY_PAGE < nb_news:
        previous_index = first + NB_NEWS_BY_PAGE + 1
    
    if first - NB_NEWS_BY_PAGE >= 0:
        next_index = first - NB_NEWS_BY_PAGE + 1
    elif first > 0:
        next_index = 1
    
    return render_to_response('news/index.html',
                              {'news_list': news_list,
                               'previous_index': previous_index,
                               'next_index': next_index,
                               'details_enabled': False,
                              },
                              context_instance=RequestContext(request))


#---------------------------------------------------------------------------------------------------
# Display a single news
#---------------------------------------------------------------------------------------------------
def news(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    return render_to_response('news/news.html',
                              {'news': news,
                               'details_enabled': True,
                              },
                              context_instance=RequestContext(request))

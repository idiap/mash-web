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


from mash.news.models import News
from mash.menu.models import MenuItem
from django.contrib import admin
import datetime


class NewsAdmin(admin.ModelAdmin):

    fields          = ('title', 'resume', 'details')
    list_display    = ('title', 'pub_date', 'author')
    list_filter     = ['pub_date']
    search_fields   = ['title', 'author']
    date_hierarchy  = 'pub_date'


    def save_model(self, request, obj, form, change):
        if not(change):
            obj.author      = request.user
            obj.pub_date    = datetime.datetime.now()
        
        obj.save()


admin.site.register(News, NewsAdmin)


class MenuItemsAdmin(admin.ModelAdmin):
    list_display = ('index', 'label', 'link')


admin.site.register(MenuItem, MenuItemsAdmin)

# -*- coding: utf-8 -*-

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


from django.contrib import admin
from phpbb.models import PhpbbForum
from phpbb.models import PhpbbPost
from phpbb.models import PhpbbTopic
from phpbb.models import PhpbbUser
from phpbb.models import PhpbbGroup
from phpbb.models import PhpbbConfig


class PhpbbForumAdmin(admin.ModelAdmin):
    list_display = ('forum_name',
                    'forum_id',
                    'forum_desc', )

admin.site.register(PhpbbForum, PhpbbForumAdmin)



class PhpbbTopicAdmin(admin.ModelAdmin):
    list_display = ('topic_title',
                    'topic_id',
                    'topic_time', )
    
admin.site.register(PhpbbTopic, PhpbbTopicAdmin)



class PhpbbPostAdmin(admin.ModelAdmin):
    list_display = ('post_id',
                    'get_absolute_url',
                    'post_time', )

admin.site.register(PhpbbPost, PhpbbPostAdmin)



class PhpbbUserAdmin(admin.ModelAdmin):
    list_display = ('username',
                    'user_id',
                    'user_regdate',
                    'user_posts',
                    'user_email', )

admin.site.register(PhpbbUser, PhpbbUserAdmin)



class PhpbbGroupAdmin(admin.ModelAdmin):
    list_display = ('group_name',
                    'group_id', )

admin.site.register(PhpbbGroup, PhpbbGroupAdmin)



class PhpbbConfigAdmin(admin.ModelAdmin):
    list_display = ('config_name',
                    'config_value',
                    'is_dynamic')

admin.site.register(PhpbbConfig, PhpbbConfigAdmin)

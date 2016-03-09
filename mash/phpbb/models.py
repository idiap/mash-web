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


from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from datetime import datetime
from django.core import exceptions
from django.utils.encoding import force_unicode
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import re
import string


def slugify(s):
    if not(isinstance(s, unicode)):
        s = unicode(s, 'utf-8')

    s = s.lower().encode('utf-8')

    return s


#---------------------------------------------------------------------------------------------------
# Represents a rank on the forum
#---------------------------------------------------------------------------------------------------
class PhpbbUserRank(models.Model):
    """Model for phpBB user rank."""

    rank_id         = models.IntegerField(primary_key=True)
    rank_title      = models.CharField(max_length=255)
    rank_min        = models.IntegerField()
    rank_special    = models.IntegerField()
    rank_image      = models.CharField(max_length=255)

    def __unicode__(self):
        return self.rank_title

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'ranks'
        ordering = ['rank_id']


#---------------------------------------------------------------------------------------------------
# Represents a forum user
#---------------------------------------------------------------------------------------------------
class PhpbbUser(models.Model):
    """Model for phpBB user."""

    user_id                     = models.IntegerField(primary_key=True)
    username                    = models.CharField(max_length=25)
    user_password               = models.CharField(max_length=32)
    user_posts                  = models.IntegerField()
    user_email                  = models.CharField(max_length=255)
    user_website                = models.CharField(max_length=100)
    user_avatar_type            = models.IntegerField()
    user_avatar                 = models.CharField(max_length=250)
    user_regdate_int            = models.IntegerField(db_column="user_regdate")
    user_lastvisit_int          = models.IntegerField(db_column="user_lastvisit")
    user_sig_bbcode_uid         = models.CharField(max_length=8)
    user_sig_bbcode_bitfield    = models.CharField(max_length=255)
    user_rank                   = models.ForeignKey(PhpbbUserRank, null=True, db_column='user_rank')
    user_from                   = models.CharField(blank=True, max_length=100)
    user_occupation             = models.TextField(blank=True, db_column='user_occ')
    user_interests              = models.TextField(blank=True)

    def __unicode__(self):
        return self.username

    def user_regdate(self):
        return datetime.fromtimestamp(self.user_regdate_int)

    def user_lastvisit(self):
        return datetime.fromtimestamp(self.user_lastvisit_int)

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'users'
        ordering = ['username']


#---------------------------------------------------------------------------------------------------
# Represents a group of users
#---------------------------------------------------------------------------------------------------
class PhpbbGroup(models.Model):
    """Model for phpBB user group."""

    GROUP_NAMES = {	'ADMINISTRATORS': 'Administrators',
                    'BOTS': 'Bots',
                    'GUESTS': 'Guests',
                    'REGISTERED': 'Registered users',
                    'REGISTERED_COPPA': 'Registered COPPA users',
                    'GLOBAL_MODERATORS': 'Global moderators',
                  }

    GROUP_TYPE_OPEN       = 4
    GROUP_TYPE_REQUEST    = 0
    GROUP_TYPE_CLOSED     = 1
    GROUP_TYPE_HIDDEN     = 2
    GROUP_TYPE_PREDEFINED = 3

    group_id        = models.IntegerField(primary_key=True)
    group_type      = models.IntegerField()
    group_name      = models.CharField(max_length=255)
    group_desc      = models.TextField()

    def __unicode__(self):
        return self.group_name

    def display_name(self):
        if PhpbbGroup.GROUP_NAMES.has_key(self.group_name):
            return PhpbbGroup.GROUP_NAMES[self.group_name]
        return self.group_name

    def nb_members(self):
        return self.users.filter(user_pending=0).count()

    def nb_pending_members(self):
        return self.users.filter(user_pending=1).count()

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'groups'
        ordering = ['group_id']


#---------------------------------------------------------------------------------------------------
# Represents the link between the users and their groups
#---------------------------------------------------------------------------------------------------
class PhpbbUserGroup(models.Model):
    """Model for phpBB user group."""

    group           = models.ForeignKey(PhpbbGroup, db_column='group_id', related_name='users')
    user            = models.ForeignKey(PhpbbUser, db_column='user_id')
    group_leader    = models.IntegerField()
    user_pending    = models.IntegerField()

    def __unicode__(self):
        return "User-group link: '" + self.user.username + "' <-> '" + self.group.group_name + "'"

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'user_group'
        ordering = ['group']


#---------------------------------------------------------------------------------------------------
# Represents a forum
#---------------------------------------------------------------------------------------------------
class PhpbbForum(models.Model):
    """Model for phpBB forum."""

    forum_id            = models.IntegerField(primary_key=True)
    forum_name          = models.CharField(max_length=60)
    forum_topics        = models.IntegerField()
    forum_topics_real   = models.IntegerField()
    forum_posts         = models.IntegerField()
    forum_last_post     = models.OneToOneField('PhpbbPost', db_column='forum_last_post_id',
                                               related_name="last_post_of_forum")
    forum_desc          = models.TextField()
    parent              = models.ForeignKey('self', related_name="child")
    left                = models.OneToOneField('self', related_name="right_of")
    right               = models.OneToOneField('self', related_name="left_of")

    def __unicode__(self):
        return force_unicode(self.forum_name)

    def __str__(self):
        return str(self.forum_name)

    def get_absolute_url(self):
        return u"/forum/%s/%s/" % (self.forum_id, self.get_slug())

    def get_slug(self):
        return slugify(self.forum_name)

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'forums'
        ordering = ['forum_name']


#---------------------------------------------------------------------------------------------------
# Represents a topic
#---------------------------------------------------------------------------------------------------
class PhpbbTopic(models.Model):
    """Model for phpBB topic."""

    topic_id                    = models.IntegerField(primary_key=True)
    topic_title                 = models.CharField(max_length=60)
    topic_replies               = models.IntegerField()
    topic_poster                = models.ForeignKey(PhpbbUser, db_column='topic_poster')
    topic_time_int              = models.IntegerField(db_column='topic_time')
    forum                       = models.ForeignKey(PhpbbForum)
    topic_last_post             = models.OneToOneField('PhpbbPost', related_name='last_post_of_topic')
    topic_first_post            = models.OneToOneField('PhpbbPost', related_name='first_post_of_topic')
    topic_last_post_time_int    = models.IntegerField(db_column='topic_last_post_time')

    def get_title(self):
        return self.topic_title

    def topic_last_post_time(self):
        return datetime.fromtimestamp(self.topic_last_post_time_int)

    def __unicode__(self):
        return self.get_title()

    def get_absolute_url(self):
        return "/forum/%s/%s/%s/" % (
        		_("topics"),
        		self.topic_id,
        		self.get_slug())

    def get_slug(self):
        return slugify(self.get_title())

    def topic_time(self):
        return datetime.fromtimestamp(self.topic_time_int)

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'topics'
        ordering = ['-topic_time_int']


#---------------------------------------------------------------------------------------------------
# Represents a post
#---------------------------------------------------------------------------------------------------
class PhpbbPost(models.Model):
    """Model for phpBB post."""

    PAGINATE_BY = 10

    post_id         = models.IntegerField(primary_key=True)
    post_subject    = models.CharField(max_length = 60)
    topic           = models.ForeignKey(PhpbbTopic)
    forum           = models.ForeignKey(PhpbbForum)
    poster          = models.ForeignKey(PhpbbUser)
    post_time_int   = models.IntegerField(db_column='post_time')
    post_text       = models.TextField()

    def post_time(self):
        return datetime.fromtimestamp(self.post_time_int)

    def __unicode__(self):
        return force_unicode(u" (post_id=%s)" % self.post_id)

    def get_absolute_url(self):
        return (u"/forum/%s/%s/%s/page%d/" %
                (_("topics"),
                 self.topic.topic_id,
                 self.topic.get_slug(),
                 self.get_page()))

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'posts'
        ordering = ['post_time_int']


#---------------------------------------------------------------------------------------------------
# Represents the configuration settings of the forum
#---------------------------------------------------------------------------------------------------
class PhpbbConfig(models.Model):
    """Model for phpBB configuration."""

    config_name     = models.CharField(max_length=255, primary_key=True)
    config_value    = models.CharField(max_length=255)
    is_dynamic      = models.IntegerField()

    def __unicode__(self):
        return self.config_name

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'config'
        ordering = ['config_name']
        verbose_name = 'Configuration entry'
        verbose_name_plural = 'Configuration entries'


#---------------------------------------------------------------------------------------------------
# Contains infos about a private message
#---------------------------------------------------------------------------------------------------
class PhpbbPrivateMessageInfos(models.Model):
    """Model for phpBB private message infos."""

    msg_id          = models.IntegerField(primary_key=True)
    user            = models.ForeignKey(PhpbbUser, related_name='private_messages')
    author          = models.ForeignKey(PhpbbUser, related_name='private_messages_sent')
    new             = models.IntegerField(db_column='pm_new')
    deleted         = models.IntegerField(db_column='pm_deleted')
    unread          = models.IntegerField(db_column='pm_unread')
    replied         = models.IntegerField(db_column='pm_replied')
    marked          = models.IntegerField(db_column='pm_marked')
    forwarded       = models.IntegerField(db_column='pm_forwarded')

    def __unicode__(self):
        return force_unicode(u" (msg_id=%s)" % self.msg_id)

    class Meta:
        db_table = settings.DATABASE_PHPBB_PREFIX + 'privmsgs_to'
        ordering = ['msg_id']

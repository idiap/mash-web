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
from django.db import connection, transaction
from django.core.files import locks
from django.contrib.auth.models import User
from phpbb.models import PhpbbPost, PhpbbTopic, PhpbbForum
import time
import os


#---------------------------------------------------------------------------------------------------
# Create the official topic of the specified "owner object"
#
# The "owner object" must have an attribute called 'post', that points to a PhpbbPost object
#---------------------------------------------------------------------------------------------------
def createTopic(owner_object, forum_name, owner_object_name, owner_object_url, owner_object_kind):

    # Lock the forum
    filename = os.path.join(settings.FORUM_ROOT, 'forum.lock')
    lock_file = open(filename, 'wb')
    try:
        os.chmod(filename, 0766)
    except:
        pass
    locks.lock(lock_file, locks.LOCK_EX)

    # Create the owner object topic if it don't already exists (it could have been
    # created while we were locked)
    if owner_object.post is None:
        forum = PhpbbForum.objects.get(forum_name=forum_name)
        
        # We can't directly use the model here, since Django refuses to save a post without a topic ID,
        # and a topic without at least one post
        cursor = connection.cursor()

        post_subject    = owner_object_name
        forum_id        = int(forum.forum_id)
        poster          = User.objects.get(username=settings.SYSTEM_ACCOUNT).get_profile().forum_user
        poster_id       = int(poster.user_id)
        post_time       = int(time.time())
        bbcode_uid      = 'deadf00d'
        post_text       = "This is the official topic of the [b:%s][url=%s/%s:%s]%s[/url:%s][/b:%s] %s." % \
                          (bbcode_uid, settings.WEBSITE_URL_DOMAIN.replace(':', '&#58;'), owner_object_url, bbcode_uid, owner_object_name,
                          bbcode_uid, bbcode_uid, owner_object_kind)

        cursor.execute("INSERT INTO `%s` (`post_subject`, `forum_id`, `poster_id`, `post_time`, `post_text`, `bbcode_uid`, `bbcode_bitfield`) VALUES ('%s', %d, %d, %d, '%s', '%s', 'UA==')" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'posts', post_subject, forum_id, poster_id, post_time, post_text, bbcode_uid))
        transaction.commit_unless_managed()

        cursor.execute("SELECT `post_id` FROM `%s` WHERE `post_subject`='%s' AND `forum_id`=%d" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'posts', post_subject, forum_id))
        row = cursor.fetchone()
        post_id = row[0]
        
        cursor.execute("INSERT INTO `%s` (`topic_title`, `forum_id`, `topic_poster`, `topic_time`, `topic_first_post_id`, `topic_last_post_id`, `topic_last_post_time`, `topic_first_poster_name`, `topic_last_poster_id`, `topic_last_poster_name`) VALUES ('%s', %d, %d, %d, %d, %d, %d, '%s', %d, '%s')" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'topics', post_subject, forum_id, poster_id, post_time, post_id, post_id, post_time, poster.username, poster_id, poster.username))
        transaction.commit_unless_managed()

        cursor.execute("SELECT `topic_id` FROM `%s` WHERE `topic_title`='%s' AND `forum_id`=%d" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'topics', post_subject, forum_id))
        row = cursor.fetchone()
        topic_id = row[0]

        cursor.execute("UPDATE `%s` SET `topic_id`=%d WHERE `post_id`=%d" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'posts', topic_id, post_id))
        transaction.commit_unless_managed()

        cursor.execute("UPDATE `%s` SET `forum_last_post_id`=%d, `forum_last_poster_id`=%d, `forum_last_post_subject`='%s', `forum_last_post_time`=%d, `forum_last_poster_name`='%s' WHERE `forum_id`=%d" % \
                       (settings.DATABASE_PHPBB_PREFIX + 'forums', post_id, poster_id, post_subject, post_time, poster.username, forum_id))
        transaction.commit_unless_managed()

        post = PhpbbPost.objects.get(pk=post_id)

        post.forum.forum_topics += 1
        post.forum.forum_topics_real += 1
        post.forum.forum_posts += 1
        post.forum.save()
        
        owner_object.post = post
        owner_object.save()
        
        poster.user_posts = poster.user_posts + 1
        poster.user_lastpost_time = post_time
        poster.save()

    # Unlock the forum
    locks.unlock(lock_file)
    lock_file.close()

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
from django.conf import settings
from django.contrib.auth.models import User
from phpbb.models import PhpbbUser, PhpbbGroup
from wiki.models import WikiUser


class UserProfile(models.Model):
    user            = models.ForeignKey(User, unique=True)
    forum_user      = models.ForeignKey(PhpbbUser, null=True)
    wiki_user       = models.ForeignKey(WikiUser, null=True)
    project_member  = models.BooleanField(default=False)
    affiliation     = models.CharField(max_length=255, null=True, blank=True)


    def __unicode__(self):
        return "User profile of '" + self.user.__unicode__() + "'"

    def public_heuristics_count(self):
        from django.db import connection, transaction
        cursor = connection.cursor()

        cursor.execute('SELECT COUNT(*) FROM heuristics_heuristic WHERE heuristics_heuristic.author_id = %d AND heuristics_heuristic.latest_public_version_id IS NOT NULL' % self.user.id)
        row = cursor.fetchone()

        return row[0]

    def private_heuristics_count(self):
        from django.db import connection, transaction
        cursor = connection.cursor()

        cursor.execute('SELECT COUNT(*) FROM heuristics_heuristic WHERE heuristics_heuristic.author_id = %d AND heuristics_heuristic.latest_public_version_id IS NULL' % self.user.id)
        row = cursor.fetchone()

        return row[0]

    def is_group_leader(self):
        return (len(self.leaded_groups()) > 0)

    def leaded_groups(self):
        return PhpbbGroup.objects.extra(where=['group_id IN (SELECT group_id ' \
                                                            'FROM %suser_group ' \
                                                            'WHERE user_id=%d ' \
                                                              'AND group_leader=1)' % (
                                                                          settings.DATABASE_PHPBB_PREFIX,
                                                                          self.forum_user.user_id)]) \
                                 .exclude(group_type=PhpbbGroup.GROUP_TYPE_PREDEFINED).order_by('group_name')

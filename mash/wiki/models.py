# -*- coding: utf-8 -*-

from django.db import models
from django.conf import settings


#---------------------------------------------------------------------------------------------------
# Represents a wiki user
#---------------------------------------------------------------------------------------------------
class WikiUser(models.Model):
    """Model for wiki user."""

    user_id     = models.IntegerField(primary_key=True)
    user_name   = models.CharField(max_length=255)
    user_email  = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.user_name
    
    class Meta:
        db_table = settings.DATABASE_MEDIAWIKI_PREFIX + 'user'
        ordering = ['user_name']

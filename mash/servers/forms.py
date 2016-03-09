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


"""
Forms and validation code for the servers

"""

from django import forms
from django.template import defaultfilters
from mash.servers.models import Server


class NewServerForm(forms.Form):

    name    = forms.CharField(max_length=200, label=u'Name', required=True,
                              help_text=u'The name of the server')
    address = forms.CharField(max_length=200, label=u'Address', required=True, 
                              help_text=u'Address of the server')
    port    = forms.IntegerField(label=u'Port', required=True,
                                 help_text=u'Port of the server')


    def clean_name(self):
        if not(self.cleaned_data.has_key('name')) or (len(self.cleaned_data['name'].strip()) == 0):
            raise forms.ValidationError(u'You must enter a name for the server')

        try:
            server = Server.objects.filter(name__iexact=self.cleaned_data['name'])[0]
            raise forms.ValidationError(u'This server name is already taken. Please enter another one.')
        except IndexError:
            pass
        
        return self.cleaned_data['name']

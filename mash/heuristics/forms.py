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
Forms and validation code for heuristics.

"""

from django import forms
from django.template import defaultfilters
from mash.heuristics.models import Heuristic


class UploadHeuristicForm(forms.Form):
    heuristic_file = forms.FileField(label=u'Heuristic file')



class HeuristicDetailsForm(forms.Form):

    heuristic_id        = forms.IntegerField(required=True, widget=forms.HiddenInput)
    name                = forms.CharField(max_length=200, label=u'Name', required=True,
                                          help_text=u'The name of your heuristic. Note that you can only change it for the private heuristics.')
    summary             = forms.CharField(max_length=512, label=u'Summary', required=False, widget=forms.Textarea,
                                          help_text=u'Please describes what your heuristic do. This will be shown when a list of heuristics is displayed.')
    description         = forms.CharField(label=u'Description', required=False, widget=forms.Textarea,
                                          help_text=u'You can write here a longer description of your heuristic. You can use the same formatting than on the wiki if you want.')
    inspirations_list   = forms.CharField(required=True, widget=forms.HiddenInput)

    def __init__(self, data, user):
        forms.Form.__init__(self, data)
        self.user = user

    def clean_name(self):
        if not(self.cleaned_data.has_key('name')) or (len(self.cleaned_data['name'].strip()) == 0):
            raise forms.ValidationError(u'You must enter a name for your heuristic.')

        dest_name = defaultfilters.slugify(self.cleaned_data['name'].strip().replace(' ', ''))

        try:
            heuristic = Heuristic.objects.filter(name__iexact=dest_name).filter(author__id=self.user.id)[0]
            if heuristic.id != int(self.data['heuristic_id']):
                raise forms.ValidationError(u'This heuristic name is already taken. Please enter another one.')
        except IndexError:
            pass
        
        return dest_name

    def clean_inspirations_list(self):
        ids = self.cleaned_data['inspirations_list'].split(';')
        cleaned_list = ';'
        for id in ids:
            if len(id) == 0:
                continue

            try:
                heuristic = Heuristic.objects.get(pk=int(id))
                cleaned_list += id + ';'
            except Heuristic.DoesNotExist:
                pass
    
        return cleaned_list

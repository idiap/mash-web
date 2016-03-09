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
Forms and validation code for the contests

"""

from django import forms
from django.template import defaultfilters
from mash.heuristics.models import HeuristicVersion


class EnterContestForm(forms.Form):

    heuristic_versions = forms.CharField(label=u'Heuristics', required=False, widget=forms.HiddenInput, initial='',
                                         help_text=u'The heuristics that will be used in the experiment')


    def clean_heuristic_versions(self):
        if not(self.cleaned_data.has_key('heuristic_versions')) or (len(self.cleaned_data['heuristic_versions']) == 0):
            raise forms.ValidationError(u'You must select some heuristics')
        
        return self.cleaned_data['heuristic_versions']

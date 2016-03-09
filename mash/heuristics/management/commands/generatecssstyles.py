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
A management command which generates CSS styles for the source code displayed on the site

"""

from django.core.management.base import BaseCommand, CommandError
from pygments.formatters import HtmlFormatter


class Command(BaseCommand):
    help = "Generates the CSS styles used to display C++ source code on the site"
    args = '<css_file>'


    def handle(self, *args, **options):
        if not(args) or (len(args) == 0):
            raise CommandError('Enter at least the path to the CSS file to generate.')

        css_file = args[0]

        output_file = open(css_file, 'w')
        output_file.write(HtmlFormatter(linenos=True, cssclass="sourcecode").get_style_defs())
        output_file.close()
        
        return "File '" + css_file + "' generated successfully"


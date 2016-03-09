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
A management command which generates a phpBB template containing the MASH top bar.
"""

from django.core.management.base import BaseCommand, CommandError
from django.template import Context, loader
from menu.models import MenuItem


class Command(BaseCommand):
    help = "Generates a phpBB template containing the MASH top bar"
    args = '<template_file [urls_prefix]>'


    def get_menu_html(self, authenticated, admin, urls_prefix):
        result = '<ul>\n'
        
        items = list(MenuItem.objects.all())
        items.sort(cmp=lambda x,y: int(x.index - y.index))
        
        for item in items:
        
            if ((item.display == 'USER') or (item.display == 'ADMIN')) and not(authenticated):
                continue
        
            if (item.display == 'ANONYMOUS') and authenticated:
                continue

            if (item.display == 'ADMIN') and not(admin):
                continue

            if item.label == 'Forum':
                result += '<li class="active"><a href="' + item.link + '"><span>' + item.label + '</span></a></li>\n'
            else:
                link = item.link
                if not(link.startswith('http://')):
                    link = urls_prefix + link
                result += '<li><a href="' + link + '"><span>' + item.label + '</span></a></li>\n'
        
        result += '</ul>'
        
        return result



    def handle(self, *args, **options):
        if not(args) or (len(args) == 0):
            raise CommandError('Enter at least the path to the templates file to generate.')

        output_file_header = args[0]
        output_file_stylesheets = args[1]
        urls_prefix = ''
        
        if len(args) == 3:
            urls_prefix = args[2]

        admin_menu = self.get_menu_html(True, True, urls_prefix)
        logged_menu = self.get_menu_html(True, False, urls_prefix)
        anonymous_menu = self.get_menu_html(False, False, urls_prefix)

        template = loader.get_template('menu/phpBB_header.html')
        context = Context({
            'urls_prefix': urls_prefix,
            'admin_menu': admin_menu,
            'logged_menu': logged_menu,
            'anonymous_menu': anonymous_menu,
        })
        output = template.render(context)

        output_file = open(output_file_header, 'w')
        output_file.write(output)
        output_file.close()
        
        template = loader.get_template('menu/phpBB_stylesheets.html')
        context = Context({
            'urls_prefix': urls_prefix,
        })
        output = template.render(context)

        output_file = open(output_file_stylesheets, 'w')
        output_file.write(output)
        output_file.close()

        return "Files '" + output_file_header + "' and '" + output_file_stylesheets + "'generated successfully"

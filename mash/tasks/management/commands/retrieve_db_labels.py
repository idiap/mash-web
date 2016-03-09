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
A management command which retrieve the labels of a given image database.
"""

from django.core.management.base import BaseCommand, CommandError
from django.template import Context, loader
from mash.tasks.models import Database, Label
from mash import settings
import sys

sys.path.append(settings.PROJECT_ROOT)

from pymash import Client, Message


class Command(BaseCommand):
    help = "Retrieve the labels of a given image database"
    args = '<db_name> [<server_address> <server_port>]'


    def handle(self, *args, **options):
        if not(args) or ((len(args) != 1) and (len(args) != 3)):
            raise CommandError('Invalid arguments, must be <db_name> [<server_address> <server_port>]')

        db_name = args[0]
        servers = []

        if len(args) == 3:
            servers.append( (args[1], int(args[2])) )

        # Retrieve the database
        try:
            db = Database.objects.get(name=db_name)
        except:
            raise CommandError("Unknown database: '%s'" % db_name)

        # Retrieve a list of servers providing the database (if necessary)
        if len(servers) == 0:
            servers = [ (server.address, server.port) for server in db.servers.all() ]

            if len(servers) == 0:
                raise CommandError("Can't find a server providing the database '%s', please indicate the address manually" % db_name)

        log = ''

        # Try each server
        for server in servers:

            log += 'Trying with server %s:%d\n' % (server[0], server[1])

            # Connection to the server
            client = Client()
            if not(client.connect(server[0], server[1])):
                log += "ERROR: Can't establish a connection with the server\n"
                continue

            # Check that the server is ready
            if not(client.sendCommand('STATUS')):
                log += "ERROR: Failed to retrieve the status of the server - transmission error\n"
                continue

            response = client.waitResponse()
            if response is None:
                log += "ERROR: Failed to retrieve the status of the server - transmission error\n"
                continue

            if response.name != 'READY':
                log += "The server isn't ready (%s)\n" % response.toString()
                continue

            # Select the database
            if not(client.sendCommand(Message('SELECT_DATABASE', [db_name]))):
                log += "ERROR: Failed to select the database - transmission error\n"
                continue

            response = client.waitResponse()
            if response is None:
                log += "ERROR: Failed to select the database - transmission error\n"
                continue

            if response.name != 'NB_IMAGES':
                log += "ERROR: Failed to select the database (got %s instead of NB_IMAGES)\n" % response.name
                continue

            response = client.waitResponse()
            if response is None:
                log += "ERROR: Failed to select the database - transmission error\n"
                continue

            if response.name != 'NB_LABELS':
                log += "ERROR: Failed to select the database (got %s instead of NB_LABELS)\n" % response.name
                continue

            response = client.waitResponse()
            if response is None:
                log += "ERROR: Failed to select the database - transmission error\n"
                continue

            if response.name != 'NB_OBJECTS':
                log += "ERROR: Failed to select the database (got %s instead of NB_OBJECTS)\n" % response.name
                continue

            # Retrieve the name of the labels
            if not(client.sendCommand('LIST_LABEL_NAMES')):
                log += "ERROR: Failed to retrieve the name of the labels - transmission error\n"
                continue

            labels = []
            while True:
                response = client.waitResponse()
                if response is None:
                    log += "ERROR: Failed to retrieve the name of the labels - transmission error\n"
                    continue

                if response.name == 'END_LIST_LABEL_NAMES':
                    break

                if response.name != 'LABEL_NAME':
                    log += "ERROR: Failed to retrieve the name of the labels - %s\n" % response.toString()
                    continue

                label = Label()
                label.index = len(labels)
                label.name = response.parameters[0]

                labels.append(label)

            # Save the retrieved names
            Label.objects.filter(database=db).delete()
            db.labels = labels

            return "Labels retrieved successfully"

        raise CommandError('Failed to retrieve the labels\nLog:\n' + log)

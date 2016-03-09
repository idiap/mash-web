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
A management command which retrieve the goals (and associated environments)
provided by goal-planning servers
"""

from django.core.management.base import BaseCommand, CommandError
from django.template import Context, loader
from mash.tasks.models import Task, Goal, Environment
from mash.servers.models import Server
from mash import settings
import sys

sys.path.append(settings.PROJECT_ROOT)

from pymash import Client, Message


class Command(BaseCommand):
    help = "Retrieve the goals (and associated environments) provided by goal-planning servers"
    args = '<task_name> [<server_name>]'


    def handle(self, *args, **options):
        if not(args) or ((len(args) != 1) and (len(args) != 2)):
            raise CommandError('Invalid arguments, must be <task_type> [<server_name>]')

        task_name = args[0]
        servers = []
        
        if len(args) == 2:
            try:
                servers.append(Server.objects.get(name=args[1]))
            except:
                raise CommandError("Unknown server: '%s'" % args[1])
        
        # Retrieve the task
        try:
            task = Task.objects.get(name=task_name)
        except:
            raise CommandError("Unknown task: '%s'" % task_name)
        
        # Retrieve a list of application servers providing the task (if necessary)
        if len(servers) == 0:
            servers = [ server for server in task.servers.filter(server_type=Server.APPLICATION_SERVER, subtype=Server.SUBTYPE_INTERACTIVE) ]

            if len(servers) == 0:
                raise CommandError("Can't find an interactive server providing the task '%s', please indicate the address manually" % task_type)

        log = ''
        
        # Try each server
        for server in servers:
        
            log += 'Trying with server %s:%d\n' % (server.address, server.port)
            
            # Connection to the server
            client = Client()
            if not(client.connect(server.address, server.port)):
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
                log += "The server isn't ready (%s)\n" % response
                continue
        
            # List the goals
            if not(client.sendCommand('LIST_GOALS')):
                log += "ERROR: Failed to list the goals - transmission error\n"
                continue
        
            response = client.waitResponse()
            if response is None:
                log += "ERROR: Failed to list the goals - transmission error\n"
                continue
        
            goals = []
            while response.name != 'END_LIST_GOALS':
                if (response.name == 'GOAL') and (len(response.parameters) == 1):
                    goals.append(response.parameters[0])
        
                    response = client.waitResponse()
                    if response is None:
                        log += "ERROR: Failed to list the goals - transmission error\n"
                        raise CommandError('Failed to retrieve the goals\nLog:\n' + log)
                else:
                    log += "ERROR: Failed to list the goals (got %s instead of GOAL or END_LIST_GOALS)\n" % response
                    raise CommandError('Failed to retrieve the goals\nLog:\n' + log)
            
            if len(goals) == 0:
                continue
        
            # Save the goals in the database
            for goal_name in goals:
                try:
                    Goal.objects.get(task=task, name=goal_name)
                except:
                    goal = Goal()
                    goal.name = goal_name
                    goal.task = task
                    goal.save()
                    
                    server.provided_goals.add(goal)
            
            # Remove the goals not provided anymore by the server
            q = server.provided_goals.exclude(name__in=goals)
            for goal in q:
                server.provided_goals.remove(goal)
        
            # List the environments for each goal
            for goal_name in goals:
                goal = Goal.objects.get(task=task, name=goal_name)
                
                if not(client.sendCommand(Message('LIST_ENVIRONMENTS', [goal_name]))):
                    log += "ERROR: Failed to list the environments - transmission error\n"
                    continue
        
                response = client.waitResponse()
                if response is None:
                    log += "ERROR: Failed to list the environments - transmission error\n"
                    continue
        
                environments = []
                while response.name != 'END_LIST_ENVIRONMENTS':
                    if (response.name == 'ENVIRONMENT') and (len(response.parameters) == 1):
                        environments.append(response.parameters[0])
        
                        response = client.waitResponse()
                        if response is None:
                            log += "ERROR: Failed to list the environments - transmission error\n"
                            raise CommandError('Failed to retrieve the goals\nLog:\n' + log)
                    else:
                        log += "ERROR: Failed to list the environments (got %s instead of ENVIRONMENT or END_LIST_ENVIRONMENTS)\n" % response
                        raise CommandError('Failed to retrieve the goals\nLog:\n' + log)
        
                # Save the environments in the database
                for environment_name in environments:
                    try:
                        environment = Environment.objects.get(name=environment_name)
                        if goal.environments.filter(id=environment.id).count() == 0:
                            goal.environments.add(environment)
                    except:
                        environment = Environment()
                        environment.name = environment_name
                        environment.save()
        
                        goal.environments.add(environment)
        
                # Remove the environments not supported anymore by the goal
                q = goal.environments.exclude(name__in=environments)
                for environment in q:
                    goal.environments.remove(environment)
        
            client.close()
        
        Goal.objects.filter(servers__isnull=True).delete()
        Environment.objects.filter(goals__isnull=True).delete()
        
        return "Goals retrieved successfully\n"

# This application requires git-python and the Git client
i################################################################################
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


mport git
import os
import subprocess
import logging

from django.core.files import locks


class GitRepository:

    def __init__(self, repository_path):
        self.root_path          = os.path.dirname(repository_path)
        self.repository_name    = os.path.basename(repository_path)
        self.lock_file_name     = self.repository_name.replace('.git', '') + '.lock'
        self.lock_file          = None
        self.nb_locks           = 0         # For this particular instance, not thread-safe


    def lock(self):
        if self.nb_locks == 0:
            filename = os.path.join(self.root_path, self.lock_file_name)
            self.lock_file = open(filename, 'wb')
            try:
                os.chmod(filename, 0766)
            except:
                pass
            locks.lock(self.lock_file, locks.LOCK_EX)

        self.nb_locks += 1
        

    def unlock(self):
        if self.nb_locks == 1:
            self.lock_file.close()
            self.lock_file = None

        self.nb_locks -= 1
        assert (self.nb_locks >= 0)
        

    def isLocked(self):
        return (self.lock_file is not None)


    def createIfNotExists(self):

        self.lock()

        try:
            fullpath = self.fullpath()
            if not(os.path.exists(fullpath)):
                current_dir = os.getcwd()

                os.makedirs(fullpath)

                os.chdir(fullpath)
                self._execute('git init')

                os.chdir(current_dir)

                self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise


    def delete(self):

        self.lock()

        try:
            fullpath = self.fullpath()
            if os.path.exists(fullpath):
                current_dir = os.getcwd()

                os.chdir(self.root_path)
                os.system("rm -rf %s" % self.repository_name)

                os.chdir(current_dir)

            self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise
    
    
    def commitFile(self, filename, message, author):

        self.lock()

        try:
            current_dir = os.getcwd()
            os.chdir(self.fullpath())

            self._execute('git add %s' % filename)
            self._execute('git commit -m "%s" --author "%s"' % (message, author))

            os.chdir(current_dir)

            self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise


    def removeFile(self, filename, message, author):

        self.lock()

        try:
            current_dir = os.getcwd()
            os.chdir(self.fullpath())

            self._execute('git rm %s' % filename)
            self._execute('git commit -m "%s" --author "%s"' % (message, author))

            os.chdir(current_dir)

            self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise


    def moveFile(self, src_filename, dst_filename, message, author):

        self.lock()

        try:
            current_dir = os.getcwd()
            os.chdir(self.fullpath())

            self._execute('git mv %s %s' % (src_filename, dst_filename))
            self._execute('git commit -m "%s" --author "%s"' % (message, author))

            os.chdir(current_dir)

            self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise


    def moveFiles(self, filenames, message, author):

        self.lock()

        try:
            current_dir = os.getcwd()
            os.chdir(self.fullpath())

            for (src, dst) in filenames:
                self._execute('git mv %s %s' % (src, dst))
        
            self._execute('git commit -m "%s" --author "%s"' % (message, author))

            os.chdir(current_dir)

            self.unlock()
        except:
            os.chdir(current_dir)
            self.unlock()
            raise


    def repository(self):
        return git.Repo(self.fullpath())
        
    
    def fullpath(self):
        return os.path.join(self.root_path, self.repository_name)


    def _execute(self, command):
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if p.wait() != 0:
            logging.error('Failed to execute the Git command: %s\n\nstdout:\n%s\n\nstderr:\n%s' %
                          (command, p.stdout.readlines(), p.stderr.readlines()))
            return False

        return True

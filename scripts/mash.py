# Utility classes and functions

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


import os
import shutil
import glob
import tarfile
import zipfile


class Packager:

    #---------------------------------------------------------------------------
    # Constructor for a packager of files in <src_path> that writes them in
    # <dst_path>/<archive_name>.tar.gz (or .zip)
    #---------------------------------------------------------------------------
    def __init__(self, src_path, dst_path, archive_name):
        self.src_path = src_path
        self.dst_path = os.path.join(dst_path, archive_name)
        self.dst_root = os.path.abspath(dst_path) + os.path.sep
        self.archive_name = archive_name

        if os.path.exists(self.dst_path):
            shutil.rmtree(self.dst_path, ignore_errors=True)
        os.makedirs(self.dst_path)

        if os.path.exists('%s.tar.gz' % self.dst_path):
            os.remove('%s.tar.gz' % self.dst_path)

        if os.path.exists('%s.zip' % self.dst_path):
            os.remove('%s.zip' % self.dst_path)

    #---------------------------------------------------------------------------
    # Copy the files corresponding to the given pattern(s) from
    # <src_path>/$(path) to <dst_path>/$(path), or <dst_path>/$(dest_path) if
    # given
    #---------------------------------------------------------------------------
    def copyFiles(self, path, patterns, dest_path=None):
        files = []
        if isinstance(patterns, str) or isinstance(patterns, unicode):
            full_pattern = os.path.join(self.src_path, path, patterns)
            files = glob.glob(full_pattern)
        else:
            for pattern in patterns:
                full_pattern = os.path.join(self.src_path, path, pattern)
                files.extend(glob.glob(full_pattern))

        if dest_path is not None:
            dest_path = os.path.join(self.dst_path, dest_path)
        else:
            dest_path = os.path.join(self.dst_path, path)

        if not(os.path.exists(dest_path)):
            os.makedirs(dest_path)

        for file in files:
            shutil.copy(file, dest_path)

    #---------------------------------------------------------------------------
    # Copy the given file from <src_path>/$(path)/$(filename) to
    # <dst_path>/$(path)/$(dest_filename)
    #---------------------------------------------------------------------------
    def copyFile(self, path, filename, dest_filename):
        src_file = os.path.join(self.src_path, path, filename)
        dest_path = os.path.join(self.dst_path, path)
        dst_file = os.path.join(dest_path, dest_filename)

        if not(os.path.exists(dest_path)):
            os.makedirs(dest_path)

        shutil.copy(src_file, dst_file)

    #---------------------------------------------------------------------------
    # Copy a tree from <src_path>/$(path) to <dst_path>/$(path), eventually
    # skipping the files corresponding to certain patterns
    #---------------------------------------------------------------------------
    def copyTree(self, path, ignore_patterns=[]):

        def ignore(path, names):
            files_to_ignore = []
            for name in ignore_patterns:
                files = glob.glob(os.path.join(path, name))
                files_to_ignore.extend(map(os.path.basename, files))
            return files_to_ignore

        def copytree(src, dst, ignore=None):
            names = os.listdir(src)
            if ignore is not None:
                ignored_names = ignore(src, names)
            else:
                ignored_names = set()

            os.makedirs(dst)
            for name in names:
                if name in ignored_names:
                    continue

                srcname = os.path.join(src, name)
                dstname = os.path.join(dst, name)

                if os.path.isdir(srcname):
                    copytree(srcname, dstname, ignore)
                else:
                    shutil.copy(srcname, dstname)

        src_path = os.path.join(self.src_path, path)
        dest_path = os.path.join(self.dst_path, path)
        copytree(src_path, dest_path, ignore=ignore)

    #---------------------------------------------------------------------------
    # Returns <dst_path>/$(path) (the full path to a file/folder in the
    # destination directory)
    #---------------------------------------------------------------------------
    def getDestPath(self, path):
        return os.path.join(self.dst_path, path)

    #---------------------------------------------------------------------------
    # Create the .tar.gz archive
    #---------------------------------------------------------------------------
    def createTarGz(self):
        tar = tarfile.open('%s.tar.gz' % self.dst_path, 'w:gz')
        tar.add(self.dst_path, arcname=self.archive_name)
        tar.close()

    #---------------------------------------------------------------------------
    # Create the .zip archive
    #---------------------------------------------------------------------------
    def createZip(self):
        zip = zipfile.ZipFile('%s.zip' % self.dst_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(self.dst_path):
            for file in files:
                path = os.path.join(root, file)
                zip.write(path, path[len(self.dst_root):])
        zip.close()

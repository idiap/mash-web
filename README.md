# MASH web application 1.0.0

http://github.com/idiap/mash-web

----------------------------

The *MASH web application* contains the source code of the front-end web server for the
"computation farm" of the **MASH project** (http://www.mash-project.eu),
developed at the **Idiap Research Institute** (http://www.idiap.ch).

It is implemented in Python, using Django 1.0.2, and was supported on Linux and MacOS X.

**NOTE THAT WE DON'T PLAN TO UPGRADE IT TO NEWER DJANGO VERSIONS. WE ARE RELEASING IT**
**FOR REFERENCE PURPOSES ONLY**

The web application include a forum (using phpBB) and a wiki (using mediawiki).


## License

The *MASH web application* is made available under the GPLv2 License. The text of the
license is in the file 'COPYING'.

    Copyright (c) 2016 Idiap Research Institute, http://www.idiap.ch/
    Written by Philip Abbet <philip.abbet@idiap.ch>

    mash-web is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 as
    published by the Free Software Foundation.

    mash-web is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with the mash-web. If not, see <http://www.gnu.org/licenses/>.


## Installation

The script 'install.py' can be used to configure the application, either in development
or production. Just execute it and follow the instructions.


## Notes

The version of the ACE JavaScript library shipped in media/js/ace/ was customized for
MASH. The affected lines are commented with the following tag: /// MASH MODIF

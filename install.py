#! /usr/bin/python

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


import sys
import os
import subprocess
import re



class DatabaseInfos:
    address     = '192.168.56.101'
    port        = 3306
    user        = 'root'
    password    = 'pwd4mash'
    name        = 'mash'


class SMTPInfos:
    server     = 'localhost'
    port        = 25
    user        = ''
    password    = ''
    use_TLS     = False
   



def check_prerequisites():
    print 'Checking prerequisites...'

    
    print '    - Checking Python version (>= 2.3.0):',

    print '%i.%i.%i' % sys.version_info[0:3],
    
    if sys.version_info >= (2, 3, 0):
        print '-> OK' 
    else:
        print '-> FAILED'
        return False
    

    print '    - Checking Django version (>= 1.0.2):',

    try:
        from django import get_version as django_version
        print django_version(),
    
        if tuple(django_version().split('.')) >= (1, 0, 2):
            print '-> OK' 
        else:
            print '-> FAILED'
            return False
    except:
        print 'Not installed'
        print 
        print 'Go to http://www.djangoproject.com to download and install Django'
        return False


    print '    - Checking MySQLdb version (>= 1.2.2):',

    try:
        from MySQLdb import version_info as mysqldb_version

        print '%i.%i.%i' % mysqldb_version[0:3],
    
        if mysqldb_version >= (1, 2, 2):
            print '-> OK' 
        else:
            print '-> FAILED'
            return False
    except:
        print 'Not installed'
        print 
        print 'Go to http://sourceforge.net/projects/mysql-python to download and install MySQLdb'
        return False


    print '    - Checking git-python version (>= 0.1.6):',

    try:
        import git
        print git.__version__,
    
        if tuple(git.__version__.split('.')) >= ('0', '1', '6'):
            print '-> OK' 
        else:
            print '-> FAILED'
            return False
    except:
        print 'Not installed'
        print 
        print 'Go to http://gitorious.org/git-python to download and install git-python'
        return False


    print '    - Checking Pygments version (>= 1.1):',

    try:
        import pygments
        print pygments.__version__,
    
        if tuple(pygments.__version__.split('.')) >= ('1', '1'):
            print '-> OK' 
        else:
            print '-> FAILED'
            print 
            print 'Go to http://pygments.org to download a newer Pygments version (you might need to download the development version using Mercurial)'
            return False
    except:
        print 'Not installed'
        print 
        print 'Go to http://pygments.org to download Pygments (you might need to download the development version using Mercurial)'
        return False


    print '    - Checking PHP version (>= 4.3.3):',

    p = subprocess.Popen("php --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print 'Not installed'
        return False

    m = re.search('^PHP (?P<version>\d\.\d\.\d) ?', p.stdout.readlines()[0])

    print m.group('version'),
    
    if tuple(m.group('version').split('.')) >= ('4', '3', '3'):
        print '-> OK' 
    else:
        print '-> FAILED'
        return False


    print '    - Checking MySQL version (>= 4.1):',

    p = subprocess.Popen("mysql --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print 'Not installed'
        return False

    m = re.search('Distrib (?P<version>\d\.\d\.\d) ?', p.stdout.readlines()[0])

    print m.group('version'),
    
    if tuple(m.group('version').split('.')) >= ('4', '1'):
        print '-> OK' 
    else:
        print '-> FAILED'
        return False


    print '    - Checking Git version (>= 1.5.0):',

    p = subprocess.Popen("git --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print 'Not installed'
        return False

    m = re.search('git version (?P<version>\d\.\d\.\d) ?', p.stdout.readlines()[0])

    print m.group('version'),
    
    if tuple(m.group('version').split('.')) >= ('1', '5', '0'):
        print '-> OK' 
    else:
        print '-> FAILED'
        return False

    print
    print """Optional requirements:

    If you want to enable the embedded math formulas on the wiki, the following
    is needed (from the README):

        OCaml 3.06 or later is required to compile texvc; this can be acquired from
        http://caml.inria.fr/ if your system doesn't have it available.

        The makefile requires GNU make.

        Rasterization is done via LaTeX, dvipng. These need to be installed and in
        the PATH: latex, dvipng

        AMS* packages for LaTeX also need to be installed. Without AMS* some equations
        will render correctly while others won't render. Most distributions of TeX
        already contain AMS*. In Debian/Ubuntu you need to install tetex-extra.

        To work properly with rendering non-ASCII Unicode characters, a supplemental TeX
        package is needed (cjk-latex in Debian)
"""

    return True

    

def connect_to_database(db):
    
    import MySQLdb
    
    try:
        connection = MySQLdb.connect(host=db.address, port=db.port, user=db.user, passwd=db.password, db=db.name)
        return connection
    except:
        return None



def get_arg(args, name, default):
    if args.has_key(name):
        return args[name]
    
    return default



def apache_configuration(**kwargs):

    print """---------------------------------------------------------------------------------
Configuration of Apache
---------------------------------------------------------------------------------"""
    print

    print
    print "    Please configure your Apache server by copying the file 'mash/apache/apache.conf'"
    print "    into the appropriate place, and modify it to use the path of your mash-web"
    print "    installation."
    print
    print "    Simply replace all instances of '/local/mash-web' with the correct path."
    print
    print "    Also modify the 'mash/apache/django.wsgi' file in the same way."

    print
    raw_input("    Press 'Enter' when you're done... ")
    print

    return True



def install_forum(**kwargs):
    
    print """---------------------------------------------------------------------------------
Installation of the phpBB3 forum
---------------------------------------------------------------------------------"""
    print

    development = get_arg(kwargs, 'development', False)
    db          = get_arg(kwargs, 'db', None)
    smtp        = get_arg(kwargs, 'smtp', None)
    web_owner   = get_arg(kwargs, 'web_owner', None)


    if not(os.path.exists('forum/config.php')):

        print "Configuration of the forum"

        os.chdir('forum')
        
        os.system("cp config_empty.php config.php")
        os.system("cp -R ../forum_install install")

        os.chmod('config.php', 0666)
        
        if web_owner is None:
            os.chmod('cache', 0777)
            os.chmod('files', 0777)
            os.chmod('store', 0777)
            os.chmod('images/avatars/upload', 0777)
        else:
            os.system("chown -R %s cache" % web_owner)
            os.system("chown -R %s files" % web_owner)
            os.system("chown -R %s store" % web_owner)
            os.system("chown -R %s images/avatars/upload" % web_owner)
            os.chmod('cache', 0755)
            os.chmod('files', 0755)
            os.chmod('store', 0755)
            os.chmod('images/avatars/upload', 0755)

        print
 
        if development:
            print "    Please configure your Apache server so that 'http://<domain>/forum' points to '%s'," % os.getcwd()
            print "    then open this URL in your browser and follow the installation procedure of phpBB."
        else:
            print "    Open the URL 'http://<domain>/forum' in your browser and follow the installation procedure of phpBB."
        
        print
        print "    The administrator username and password you will choose here must be the same"
        print "    than the ones of the wiki and django superuser you will create later!"
        print
        print "    It is recommended to choose the 'phpbb_' prefix for the database tables."

        print
        raw_input("    Press 'Enter' when you're done... ")
        print

        os.chmod('config.php', 0644)
 
        os.system("rm -rf install")

        os.chdir('..')


    print "Modification of the DB tables..."

    p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s < sql/phpbb.sql" %
                         (db.address, db.port, db.user, db.password, db.name),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print "    FAILED to import the file 'sql/phpbb.sql' into the database"
        print
        print "Standard output of the mysql program:"
        print p.stdout.read()
        print
        print "Standard error of the mysql program:"
        print p.stderr.read()
        return False


    print "Configure the forum as 'Emdedded in MASH main site'..."

    in_file = open('forum/config.php', 'r')
    content = in_file.read()
    in_file.close()

    if content.find('MASH_WEBSITE_EMBEDDING') < 0:

        if development:
            content = content.replace("?>", "@define('MASH_WEBSITE_EMBEDDING', true);\n@define('MASH_WEBSITE_DOMAIN', 'http://localhost:8000');\n?>")
        else:
            content = content.replace("?>", "@define('MASH_WEBSITE_EMBEDDING', true);\n@define('MASH_WEBSITE_DOMAIN', '');\n?>")
        content = content.replace("EMAIL_USE_TLS       = False",    "EMAIL_USE_TLS       = " + str(smtp.use_TLS), 1)

        out_file = open('forum/config.php', 'w')
        out_file.write(content)
        out_file.close()

        in_file = open('forum/includes/auth/getdjangouser.php.template', 'r')
        content = in_file.read()
        in_file.close()

        content = content.replace('<DB_SERVER>', '"%s"' % db.address)
        content = content.replace('<DB_USER>', '"%s"' % db.user)
        content = content.replace('<DB_PASSWORD>', '"%s"' % db.password)
        content = content.replace('<DB_TABLE>', '"%s"' % db.name)

        out_file = open('forum/includes/auth/getdjangouser.php', 'w')
        out_file.write(content)
        out_file.close()

    else:
    
        print
        print "    The file 'forum/config.php' seems to already contain the needed settings"


    return True



def install_wiki(**kwargs):

    print """---------------------------------------------------------------------------------
Installation of the MediaWiki wiki
---------------------------------------------------------------------------------"""
    print

    development = get_arg(kwargs, 'development', False)
    web_owner   = get_arg(kwargs, 'web_owner', None)


    if not(os.path.exists('wiki/LocalSettings.php')):

        print "Configuration of the wiki"

        os.chdir('wiki')

        os.system("cp -R ../wiki_config config")

        os.chmod('config', 0777)

        if web_owner is None:
            os.chmod('images', 0777)
        else:
            os.system("chown -R %s images" % web_owner)
            os.chmod('images', 0755)

        print

        if development:
            print "    Please configure your Apache server so that 'http://<domain>/wiki' points to '%s'," % os.getcwd()
            print "    then open 'http://<domain>/wiki/config' in your browser and follow the installation procedure of MediaWiki."
        else:
            print "    Open the URL 'http://<domain>/wiki/config' in your browser and follow the installation procedure of MediaWiki."

        print
        print "    The administrator username and password you will choose here must be the same"
        print "    than the ones of the forum and django superuser you will create later!"
        print
        print "    It is recommended to choose the 'mw_' prefix for the database tables."

        print
        raw_input("    Press 'Enter' when you're done... ")
        print

        os.system("mv config/LocalSettings.php .")
        os.system("rm -rf config")


        print "Modification the configuration of the wiki..."

        in_file = open('LocalSettings.php', 'r')
        content = in_file.read()
        in_file.close()

        lines = content.splitlines()

        # Change the default style
        index = lines.index(filter(lambda x: x.startswith('$wgDefaultSkin'), lines)[0])
        lines[index] = "$wgDefaultSkin = 'mash';"

        # Enable uploads
        index = lines.index(filter(lambda x: x.startswith('$wgEnableUploads'), lines)[0])
        lines[index] = '$wgEnableUploads = true;'

        # Enable embedded math formulas
        print
        enableMath = (raw_input("    Do you want to enable embedded math formulas? (y/n, default: n): ") == 'y')
        print

        if enableMath:
            os.chdir('math')

            p = subprocess.Popen("make", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if p.wait() == 0:
                index = lines.index(filter(lambda x: x.startswith('$wgUseTeX'), lines)[0])
                lines[index] = '$wgUseTeX = true;'
            else:
                print "        FAILED to compile texvc"
                print
                print "Standard output of make:"
                print p.stdout.read()
                print
                print "Standard error of make:"
                print p.stderr.read()
                print

            os.chdir('..')
            
        content = '\n'.join(lines)
        
        content += """
# Disable anonymous editing
$wgGroupPermissions['*']['edit'] = false;

# Prevent new user registrations except by sysops
$wgGroupPermissions['*']['createaccount'] = false;

# Users can't create pages
$wgGroupPermissions['*']['createpage'] = false;
$wgGroupPermissions['user']['createpage'] = false;
$wgGroupPermissions['autoconfirmed']['createpage'] = false;
$wgGroupPermissions['sysop']['createpage'] = true;

# Hidden namespace
$wgExtraNamespaces = array(
                100 => "Consortium",
				101 => "Consortium_Talk");

$wgRestrictedNamespaces = array(
                100 => "ConsortiumGrp",
				101 => "Consortium_TalkGrp");

$wgNonincludableNamespaces = array(
                100,
        		101);

$wgGroupPermissions['consortium']['ConsortiumGrp']       = true;
$wgGroupPermissions['consortium']['Consortium_TalkGrp']  = true;

# Prevent users from choosing their skin
$wgAllowUserSkin = false;

# Use our custom authentication mecanism
require_once("$IP/extensions/AuthViaDjango/AuthViaDjango.php");
$wgCachePages = false;

$wgShowIPinHeader = false;

# GeshiCodeTag extension
include("extensions/GeshiCodeTag.php");

"""

        if development:
            content += "# Configure the wiki as embedded in the MASH main site\n@define('MASH_WEBSITE_EMBEDDING', true);\n@define('MASH_WEBSITE_DOMAIN', 'http://localhost:8000');\n"
        else:
            content += "# Configure the wiki as embedded in the MASH main site\n@define('MASH_WEBSITE_EMBEDDING', true);\n@define('MASH_WEBSITE_DOMAIN', '');\n"

        out_file = open('LocalSettings.php', 'w')
        out_file.write(content)
        out_file.close()
        
        if not(development):
            os.chmod('LocalSettings.php', 0600)

        os.chdir('..')

        print "Modification of the DB tables..."

        p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s < sql/wiki.sql" %
                             (db.address, db.port, db.user, db.password, db.name),
                             shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if p.wait() != 0:
            print "    FAILED to import the file 'sql/wiki.sql' into the database"
            print
            print "Standard output of the mysql program:"
            print p.stdout.read()
            print
            print "Standard error of the mysql program:"
            print p.stderr.read()
            return False

    return True



def install_django_applications(**kwargs):
    
    print """---------------------------------------------------------------------------------
Installation of the Django applications
---------------------------------------------------------------------------------"""
    print

    development = get_arg(kwargs, 'development', False)
    db          = get_arg(kwargs, 'db', None)
    smtp        = get_arg(kwargs, 'smtp', None)
    web_owner   = get_arg(kwargs, 'web_owner', None)


    print "Creation of the settings file..."

    if not(os.path.exists('mash/settings.py')):

        in_file = open('mash/settings_example.py', 'r')
        content = in_file.read()
        in_file.close()
        
        content = content.replace("PROJECT_ROOT = ''", "PROJECT_ROOT = '" + os.getcwd() + "/'", 1)
        
        if not(development):
            content = content.replace("DEVELOPMENT_SERVER = True", "DEVELOPMENT_SERVER = False", 1)

        if db is not None:
            content = content.replace("DATABASE_NAME               = ''", "DATABASE_NAME               = '" + db.name + "'", 1)
            content = content.replace("DATABASE_USER               = ''", "DATABASE_USER               = '" + db.user + "'", 1)
            content = content.replace("DATABASE_PASSWORD           = ''", "DATABASE_PASSWORD           = '" + db.password + "'", 1)
            content = content.replace("DATABASE_HOST               = ''", "DATABASE_HOST               = '" + db.address + "'", 1)
            content = content.replace("DATABASE_PORT               = ''", "DATABASE_PORT               = '" + str(db.port) + "'", 1)

        if smtp is not None:
            content = content.replace("EMAIL_HOST          = ''",       "EMAIL_HOST          = '" + smtp.server + "'", 1)
            content = content.replace("EMAIL_PORT          = 0",        "EMAIL_PORT          = " + str(smtp.port), 1)
            content = content.replace("EMAIL_HOST_USER     = ''",       "EMAIL_HOST_USER     = '" + smtp.user + "'", 1)
            content = content.replace("EMAIL_HOST_PASSWORD = ''",       "EMAIL_HOST_PASSWORD = '" + smtp.password + "'", 1)
            content = content.replace("EMAIL_USE_TLS       = False",    "EMAIL_USE_TLS       = " + str(smtp.use_TLS), 1)

        out_file = open('mash/settings.py', 'w')
        out_file.write(content)
        out_file.close()
        
        print
        print "    The 'mash/settings.py' file was created successfully, please check its content"
    else:
        print
        print "    The 'mash/settings.py' file already exists, please review its content"

    print
    raw_input("    Press 'Enter' when you're done... ")
    print
    
    
    print "Creation of the tables in the database..."

    p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s < sql/schema.sql" %
                         (db.address, db.port, db.user, db.password, db.name),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print "    FAILED to import the file 'sql/schema.sql' into the database"
        return False


    print "Synchronization of the database..."

    print
    print "    When asked for, create a superuser with the same username and password than the"
    print "    forum administrator created earlier"

    print
    raw_input("    Press 'Enter' to continue... ")
    print

    os.chdir('mash')
    os.system('python manage.py syncdb')
    os.chdir('..')


    print "Importation of the data in the database..."

    sqldata = 'sql/data.sql'
    p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s < %s" %
                         (db.address, db.port, db.user, db.password, db.name, sqldata),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.wait() != 0:
        print "    FAILED to import the file '%s' into the database" % sqldata
        return False


    print "Generation of the forum and wiki headers..."

    os.chdir('mash')
    
    if development:
        os.system('python manage.py generate_forum_menu ../forum/styles/mash/template/mash_header.html ../forum/styles/mash/template/mash_stylesheets.html http://localhost:8000')
        os.system('python manage.py generate_wiki_menu ../wiki/skins/mash_header.php ../wiki/skins/mash_stylesheets.php http://localhost:8000')
    else:
        os.system('python manage.py generate_forum_menu ../forum/styles/mash/template/mash_header.html ../forum/styles/mash/template/mash_stylesheets.html')
        os.system('python manage.py generate_wiki_menu ../wiki/skins/mash_header.php ../wiki/skins/mash_stylesheets.php')
    

    print "Generation of the CSS stylesheet for the C++ source code..."

    os.system('python manage.py generatecssstyles ../media/css/sourcecode.css')

    os.chdir('..')


    print "Changing owner/rights of the 'media/files' folder..."

    if web_owner is None:
        os.chmod('media/files', 0777)
    else:
        os.system("chown -R %s media/files" % web_owner)
        os.chmod('media/files', 0755)


    return True



def setup_repository(path, name):
    
    print "Repository '%s'" % name
    print

    import git

    fullpath = os.path.join(path, name)

    try:
        repo = git.Repo(fullpath)
        print "    Repository '%s' already created" % name
        return True
    except:
        pass


    url = raw_input('    Enter the URL of the repository to clone, or leave blank to create a new one: ')

    current_dir = os.getcwd()

    if len(url) == 0:
        if not(os.path.exists(fullpath)):
            os.makedirs(fullpath)
    
        os.chdir(fullpath)
        ret = os.system('git init')
    else:
        if not(os.path.exists(path)):
            os.makedirs(path)
    
        os.chdir(path)
        ret = os.system('git clone %s %s' % (url, name))

    os.chdir(current_dir)

    if ret != 0:
        print
        print "    FAILED to create the '%s' repository in the '%s' folder" % (name, path)
        return False


    try:
        repo = git.Repo(fullpath)
    except:
        print
        print "    FAILED to access the '%s' repository in the '%s' folder" % (name, path)
        return False

    return True



def setup_heuristics_repository(**kwargs):
    
    print """---------------------------------------------------------------------------------
Setup of the Git repositories
---------------------------------------------------------------------------------"""
    print

    development = get_arg(kwargs, 'development', False)
    web_owner   = get_arg(kwargs, 'web_owner', None)

    if not(setup_repository('repositories', 'heuristics.git')):
        return False

    print

    if not(setup_repository('repositories', 'upload.git')):
        return False

    print

    if not(development):
        os.system('chown -R %s heuristics' % web_owner)

    return True



def setup_system_account(**kwargs):

    print """---------------------------------------------------------------------------------
Setup of the system account
---------------------------------------------------------------------------------"""
    print

    db = get_arg(kwargs, 'db', None)

    print
    print "Open the website in your browser and create an account called 'MASH'"
    print "(or wathever you choose in the 'settings.py' file for the 'SYSTEM_ACCOUNT'"
    print "setting). You don't need to provide a valid e-mail address. Don't "
    print "activate the account."

    print
    raw_input("Press 'Enter' to continue... ")
    print

    account_name = raw_input("The account name you choose ('MASH'): ")
    if len(account_name) == 0:
        account_name = 'MASH'
    
    print "Activation of the system account..."

    sql_file = open('sql/system_account_activation.sql', 'r')
    sql = sql_file.read().replace('$ACCOUNT_NAME', account_name)
    sql_file.close()

    p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s" %
                         (db.address, db.port, db.user, db.password, db.name),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)

    p.stdin.write(sql)
    p.stdin.close()

    if p.wait() != 0:
        print "    FAILED to activate the system account"
        return False

    print
    print "Log onto the website with the system account you just created. Edit its"
    print "profile to your liking. Use the following URL for the avatar:"
    print "'http://<domain>/images/system_account_avatar.png'"

    print
    raw_input("Press 'Enter' to continue... ")
    print

    print "Setup of the forum permissions of the system account..."

    sql_file = open('sql/system_account_forum.sql', 'r')
    sql = sql_file.read().replace('$ACCOUNT_NAME', account_name)
    sql_file.close()

    p = subprocess.Popen("mysql --host=%s --port=%i --user=%s --pass=%s %s" %
                         (db.address, db.port, db.user, db.password, db.name),
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)

    p.stdin.write(sql)
    p.stdin.close()

    if p.wait() != 0:
        print "    FAILED to setup the forum permissions"
        return False

    return True
    


print '*********************************************************************************'
print '*                                                                               *'
print '*                      MASH WEBSITE INSTALLATION SCRIPT                         *'
print '*                                                                               *'
print '*********************************************************************************'
print ''

target_step = None

if len(sys.argv) == 2:
    if (sys.argv[1] == '-h') or (sys.argv[1] == '--help'):
        print 'Usage: %s [phase]' % sys.argv[0]
        print 'Available phases: apache, forum, wiki, django, repositories, system_account'
        sys.exit(0)
    else:
        target_step = sys.argv[1]

if not(check_prerequisites()):
    sys.exit(-1)

print

print """---------------------------------------------------------------------------------
There is two modes of installation: Production and Development.

In a Development environment, the forum and the wiki are served by an Apache
server and the Django applications by the standalone Django server. This allows
Django to notice any change in the Python scripts, and to reload them when
needed.

In a Production environment, everything is served by Apache, which means that
it must be restarted for any change to take effect.
---------------------------------------------------------------------------------"""
print

development = (raw_input('Do you want to install a production environment? (y/n): ') != 'y')
print


# The format is: (STEP_NAME, FUNCTION, NEEDS_DB, NEEDS_SMTP, NEEDS_WEB_OWNER)
SETUP_FUNCTIONS = [ ('forum', install_forum, True, True, True),
                    ('wiki', install_wiki, True, False, True),
                    ('django', install_django_applications, True, True, True),
                    ('repositories', setup_heuristics_repository, False, False, True),
                    ('system_account', setup_system_account, True, False, False),
                  ]

if not(development):
    SETUP_FUNCTIONS.insert(0, ('apache', apache_configuration, False, False, False))


db = None
db_connection = None
smtp = None
web_owner = None

for (step, function, needs_db, needs_smtp, needs_web_owner) in SETUP_FUNCTIONS:

    if (target_step is not None) and (target_step != step):
        continue

    if needs_db and (db is None):
        print """---------------------------------------------------------------------------------
Database settings
---------------------------------------------------------------------------------"""
        print

        db = DatabaseInfos()

        db.address = raw_input("Database address ('localhost'): ")
        if len(db.address) == 0:
            db.address = 'localhost'

        db.port = raw_input("Database port (3306): ")
        if len(db.port) == 0:
            db.port = 3306
        else:
            db.port = int(db.port)

        db.user = raw_input("Database user ('mash'): ")
        if len(db.user) == 0:
            db.user = 'mash'

        db.password = raw_input("Database password ('pwd4mash'): ")
        if len(db.password) == 0:
            db.password = 'pwd4mash'

        db.name = raw_input("Database name ('mash'): ")
        if len(db.name) == 0:
            db.name = 'mash'

        print 

        print "Test the connection with the database...",

        db_connection = connect_to_database(db)
        if db_connection is not None:
            print "OK"
        else:
            print "FAILED"
            print
            print "Please create the necessary user and database on the server"
            sys.exit(-1)

        print

    if needs_smtp and (smtp is None):
        print """---------------------------------------------------------------------------------
SMTP server settings
---------------------------------------------------------------------------------"""
        print

        smtp = SMTPInfos()

        smtp.server = raw_input("SMTP server ('localhost'): ")
        if len(smtp.server) == 0:
            smtp.server = 'localhost'

        if development:
            smtp.port = 1025

        smtp.port = raw_input("SMTP port (%i): " % smtp.port)
        if len(smtp.port) == 0:
            if development:
                smtp.port = 1025
            else:
                smtp.port = 25
        else:
            smtp.port = int(smtp.port)

        smtp.user = raw_input("SMTP user (''): ")
        smtp.password = raw_input("SMTP password (''): ")

        smtp.use_TLS = (raw_input("Use TLS (y/n, default: n): ") == 'y')

        print
        
    if needs_web_owner and (web_owner is None) and not(development):
        print """---------------------------------------------------------------------------------
Web-server settings
---------------------------------------------------------------------------------"""
        print

        if not(development):
            web_owner = raw_input("Web-server user/group ('www-data:www-data'): ")
            if len(web_owner) == 0:
                web_owner = 'www-data:www-data'
        else:
            web_owner = None
    
    if not(function(development=development, db=db, smtp=smtp, web_owner=web_owner)):
        sys.exit(-1)
    
    print


if db_connection is not None:
    db_connection.close()

print 
print 'Installation successfull!'

if not(development) and (target_step is None):
    print
    print "Note that you must still symlink <DJANGO_ROOT>/contrib/admin/media to admin-media"

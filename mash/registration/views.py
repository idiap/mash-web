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
Views which allow users to create and activate accounts.

"""


from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.sites.models import Site

from registration.forms import RegistrationForm
from registration.models import RegistrationProfile

import captcha
#added
from django.utils import simplejson
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import defaultfilters
from mash.heuristics.models import Heuristic
from mash.heuristics.models import HeuristicVersion
from mash.heuristics.models import HeuristicTestStatus
from mash.heuristics.utilities import *
from mash.experiments.views import schedule_experiment
from mash.experiments.models import Configuration, Experiment
from pymash.gitrepository import GitRepository
from pymash.messages import Message
from servers import acquireExperimentsScheduler, releaseExperimentsScheduler
from datetime import datetime, date, timedelta
import os
import shutil


def activate(request, activation_key,
             template_name='registration/activate.html',
             extra_context=None):
    """
    Activate a ``User``'s account from an activation key, if their key
    is valid and hasn't expired.
    
    By default, use the template ``registration/activate.html``; to
    change this, pass the name of a template as the keyword argument
    ``template_name``.
    
    **Required arguments**
    
    ``activation_key``
       The activation key to validate and use for activating the
       ``User``.
    
    **Optional arguments**
       
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.
    
    ``template_name``
        A custom template to use.
    
    **Context:**
    
    ``account``
        The ``User`` object corresponding to the account, if the
        activation was successful. ``False`` if the activation was not
        successful.
    
    ``expiration_days``
        The number of days for which activation keys stay valid after
        registration.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/activate.html or ``template_name`` keyword argument.
    
    """
    activationKey = activation_key.lower() # Normalize before trying anything with it.

    user = request.user
    anonuser_db=''
    cookie_value = ""
    if request.COOKIES.has_key('robot_uid'):
        cookie_value = request.COOKIES.__getitem__('robot_uid')
        #user is anonymous
        anonUser = "anon_%s"%cookie_value
        #check if anonymous user has already used the system
        try :
            anonuser_db = User.objects.all().get(username=anonUser)
            #only display simple heuristics from current user
            heuristiclist = HeuristicVersion.objects.filter(heuristic__simple=True).filter(heuristic__author__id=anonuser_db.id)
            userFromActivationKey = RegistrationProfile.objects.all().get(activation_key="%s"%activationKey)
            userToActivate = User.objects.all().get(id=userFromActivationKey.user.id)
            #modify author_id
            for simpleHeuristic in heuristiclist:
                version = get_object_or_404(HeuristicVersion, pk=simpleHeuristic.id)
                heuristic = get_object_or_404(Heuristic, pk=simpleHeuristic.heuristic_id)
                heuristic.author = userFromActivationKey.user
                heuristic.save()

                # Retrieve the repository containing the source file and lock it
                if version.checked:
                    repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_HEURISTICS))
                else:
                    repo = GitRepository(os.path.join(settings.REPOSITORIES_ROOT, settings.REPOSITORY_UPLOAD))
                repo.lock()

                try:
                    # move repository folder from anonymous to newly registered user
                    repo.moveFile('%s' % (anonUser), '%s' % (userToActivate.username.lower()),
                    "Simple Heuristic '%s' moved to registered user (by %s)" % (heuristiclist, userToActivate.username),
                    settings.COMMIT_AUTHOR)
                except:
                    pass

                # Release the lock
                repo.unlock()
            #delete anonymous user from database
            anonuser_db.delete()


        except User.DoesNotExist :
            #Not found anonymous user
            pass
        #anonymous user is refered by anon_<cookievalue>
    else :
        #no cookie
        pass
    
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    account = RegistrationProfile.objects.activate_user(activation_key)
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                                'site': Site.objects.get_current() },
                              context_instance=context)


def register(request, success_url=None,
             form_class=RegistrationForm,
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register an account.
    
    Following successful registration, issue a redirect; by default,
    this will be whatever URL corresponds to the named URL pattern
    ``registration_complete``, which will be
    ``/accounts/register/complete/`` if using the included URLConf. To
    change this, point that named pattern at another URL, or pass your
    preferred URL as the keyword argument ``success_url``.
    
    By default, ``registration.forms.RegistrationForm`` will be used
    as the registration form; to change this, pass a different form
    class as the ``form_class`` keyword argument. The form class you
    specify must have a method ``save`` which will create and return
    the new ``User``.
    
    By default, use the template
    ``registration/registration_form.html``; to change this, pass the
    name of a template as the keyword argument ``template_name``.
    
    **Required arguments**
    
    None.
    
    **Optional arguments**
    
    ``form_class``
        The form class to use for registration.
    
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.
    
    ``success_url``
        The URL to redirect to on successful registration.
    
    ``template_name``
        A custom template to use.
    
    **Context:**
    
    ``form``
        The registration form.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/registration_form.html or ``template_name`` keyword
    argument.
    
    """
    test_cookie_worked = True
        
    if request.method == 'POST':

        # Check the test cookie
        test_cookie_worked = request.session.test_cookie_worked()
        if test_cookie_worked:
            request.session.delete_test_cookie()

        # Check the captcha
        if settings.ACCOUNT_REGISTRATION_USE_RECAPTCHA:
            try:
                check_captcha = captcha.submit(request.POST['recaptcha_challenge_field'], request.POST['recaptcha_response_field'],
                                               settings.RECAPTCHA_PRIVATE_KEY, request.META['REMOTE_ADDR'])
            except KeyError:  # To avoid getting error e-mails when spammers fail at scripting ;)
                check_captcha = captcha.RecaptchaResponse(is_valid=False)
        
        # Check the form
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid() and test_cookie_worked and (not(settings.ACCOUNT_REGISTRATION_USE_RECAPTCHA) or check_captcha.is_valid):
            new_user = form.save()
            # success_url needs to be dynamically generated here; setting a
            # a default value using reverse() will cause circular-import
            # problems with the default URLConf for this application, which
            # imports this file.
            return HttpResponseRedirect(success_url or reverse('registration_complete'))

        if settings.ACCOUNT_REGISTRATION_USE_RECAPTCHA and not(check_captcha.is_valid):
            form.errors['captcha'] = '<ul class="errorlist"><li>Incorrect CAPTCHA solution.</li></ul>'
    else:
        form = form_class()
    
    if extra_context is None:
        extra_context = {}

    request.session.set_test_cookie()
    
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    
    html_captcha = None
    if settings.ACCOUNT_REGISTRATION_USE_RECAPTCHA:
        html_captcha = captcha.displayhtml(settings.RECAPTCHA_PUB_KEY)
    
    return render_to_response(template_name,
                              { 'form': form,
                                'captcha': html_captcha,
                                'test_cookie_worked': test_cookie_worked, },
                              context_instance=context)

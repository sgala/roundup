# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# IN NO EVENT SHALL BIZAR SOFTWARE PTY LTD BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# BIZAR SOFTWARE PTY LTD SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS"
# BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
# 
# $Id: ZRoundup.py,v 1.10 2002/09/04 02:05:19 richard Exp $
#
''' ZRoundup module - exposes the roundup web interface to Zope

This frontend works by providing a thin layer that sits between Zope and the
regular CGI interface of roundup, providing the web frontend with the minimum
of effort.

This means that the regular CGI interface does all authentication quite
independently of Zope. The roundup code is kept in memory though, and it
runs in the same server as all your other Zope stuff, so it does have _some_
advantages over regular CGI :)

It also means that any requests which specify :filter, :columns or :sort
_must_ be done using a GET, so that this interface can re-parse the
QUERY_STRING. Zope interprets the ':' as a special character, and the special
args are lost to it.
'''

import urlparse

from Globals import InitializeClass, HTMLFile
from OFS.SimpleItem import Item
from OFS.PropertyManager import PropertyManager
from Acquisition import Implicit
from Persistence import Persistent
from AccessControl import ClassSecurityInfo
from AccessControl import ModuleSecurityInfo
modulesecurity = ModuleSecurityInfo()

import roundup.instance
from roundup.cgi import NotFound

modulesecurity.declareProtected('View management screens',
    'manage_addZRoundupForm')
manage_addZRoundupForm = HTMLFile('dtml/manage_addZRoundupForm', globals())

modulesecurity.declareProtected('Add Z Roundups', 'manage_addZRoundup')
def manage_addZRoundup(self, id, instance_home, REQUEST):
    """Add a ZRoundup product """
    # validate the instance_home
    roundup.instance.open(instance_home)
    self._setObject(id, ZRoundup(id, instance_home))
    return self.manage_main(self, REQUEST)

class RequestWrapper:
    '''Make the Zope RESPONSE look like a BaseHTTPServer
    '''
    def __init__(self, RESPONSE):
        self.RESPONSE = RESPONSE
        self.wfile = self.RESPONSE
    def send_response(self, status):
        self.RESPONSE.setStatus(status)
    def send_header(self, header, value):
        self.RESPONSE.addHeader(header, value)
    def end_headers(self):
        # not needed - the RESPONSE object handles this internally on write()
        pass

class FormItem:
    '''Make a Zope form item look like a cgi.py one
    '''
    def __init__(self, value):
        self.value = value
        if hasattr(self.value, 'filename'):
            self.filename = self.value.filename
            self.file = self.value

class FormWrapper:
    '''Make a Zope form dict look like a cgi.py one
    '''
    def __init__(self, form):
        self.form = form
    def __getitem__(self, item):
        return FormItem(self.form[item])
    def has_key(self, item):
        return self.form.has_key(item)
    def keys(self):
        return self.form.keys()

class ZRoundup(Item, PropertyManager, Implicit, Persistent):
    '''An instance of this class provides an interface between Zope and
       roundup for one roundup instance
    '''
    meta_type =  'Z Roundup'
    security = ClassSecurityInfo()

    def __init__(self, id, instance_home):
        self.id = id
        self.instance_home = instance_home

    # define the properties that define this object
    _properties = (
        {'id':'id', 'type': 'string', 'mode': 'w'},
        {'id':'instance_home', 'type': 'string', 'mode': 'w'},
    )
    property_extensible_schema__ = 0

    # define the tabs for the management interface
    manage_options= PropertyManager.manage_options + (
        {'label': 'View', 'action':'index_html'},
    ) + Item.manage_options

    icon = "misc_/ZRoundup/icon"

    security.declarePrivate('_opendb')
    def _opendb(self):
        '''Open the roundup instance database for a transaction.
        '''
        instance = roundup.instance.open(self.instance_home)
        request = RequestWrapper(self.REQUEST['RESPONSE'])
        env = self.REQUEST.environ

        # figure out the path components to set
        url = urlparse.urlparse( self.absolute_url() )
        path = url[2]
        path_components = path.split( '/' )
                                                
        # special case when roundup is '/' in this virtual host,
        if path == "/" :
            env['SCRIPT_NAME'] = "/"
            env['INSTANCE_NAME'] = ''
        else :
            # all but the last element is the path
            env['SCRIPT_NAME'] = '/'.join( path_components[:-1] )
            # the last element is the name
            env['INSTANCE_NAME'] = path_components[-1]

        if env['REQUEST_METHOD'] == 'GET':
            # force roundup to re-parse the request because Zope fiddles
            # with it and we lose all the :filter, :columns, etc goodness
            form = None
        else:
            # For some reason, CRs are embeded in multiline notes.
            # It doesn't occur with apache/roundup.cgi, though.
            form = self.REQUEST.form 
            if form.has_key( '__note' ) :
                form['__note'] = form['__note'].replace( '\r' , '' )
            form = FormWrapper(form)

        return instance.Client(instance, request, env, form)


    security.declareProtected('View', 'index_html')
    def index_html(self):
        '''Alias index_html to roundup's index
        '''

        # Redirect misdirected requests -- bugs 558867 , 565992
       
        # PATH_INFO, as defined by the CGI spec, has the *real* request path
        orig_path = self.REQUEST.environ[ 'PATH_INFO' ]
        if orig_path[-1] != '/' : 
            url = urlparse.urlparse( self.absolute_url() )
            url = list( url ) # make mutable
            url[2] = url[2]+'/' # patch
            url = urlparse.urlunparse( url ) # reassemble
            RESPONSE = self.REQUEST.RESPONSE
            RESPONSE.setStatus( "MovedPermanently" ) # 301
            RESPONSE.setHeader( "Location" , url )
            return RESPONSE

        client = self._opendb()
        # fake the path that roundup should use
        client.split_path = ['index']
        return client.main()

    def __getitem__(self, item):
        '''All other URL accesses are passed throuh to roundup
        '''
        try:
            client = self._opendb()
            # fake the path that roundup should use
            client.split_path = [item]
            # and call roundup to do something 
            client.main()
            return ''
        except NotFound:
            raise 'NotFound', self.REQUEST.URL
            pass
        except:
            import traceback
            traceback.print_exc()
            # all other exceptions in roundup are valid
            raise
        raise KeyError, item


InitializeClass(ZRoundup)
modulesecurity.apply(globals())


#
# $Log: ZRoundup.py,v $
# Revision 1.10  2002/09/04 02:05:19  richard
# new cgi client here too
#
# Revision 1.9  2002/07/04 01:25:22  dman13
# fixed #576086 (dumb copying mistake)
#
# Revision 1.8  2002/06/16 01:01:42  dman13
# remove CR characters embedded in messages (ZRoundup)
#
# Revision 1.7  2002/06/14 01:25:46  dman13
# Fixed bug #558867 by redirecting /instance requests to /instance/
#
# Revision 1.6  2002/06/12 00:59:44  dman13
# Fixed the logic for determing the cookie path.  (Closes #562130.)
#
# Revision 1.5  2002/05/14 23:36:25  richard
#  . fixed SCRIPT_NAME in ZRoundup for instances not at top level of Zope
#    (thanks dman)
#
# Revision 1.4  2002/01/10 03:38:16  richard
# reformatting for 80 cols
#
# Revision 1.3  2001/12/12 23:55:00  richard
# Fixed some problems with user editing
#
# Revision 1.2  2001/12/12 23:33:58  richard
# added some implementation notes
#
# Revision 1.1  2001/12/12 23:27:13  richard
# Added a Zope frontend for roundup.
#
#
#
# vim: set filetype=python ts=4 sw=4 et si

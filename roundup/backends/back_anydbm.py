#
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
#$Id: back_anydbm.py,v 1.17 2001/12/14 23:42:57 richard Exp $
'''
This module defines a backend that saves the hyperdatabase in a database
chosen by anydbm. It is guaranteed to always be available in python
versions >2.1.1 (the dumbdbm fallback in 2.1.1 and earlier has several
serious bugs, and is not available)
'''

import whichdb, anydbm, os, marshal
from roundup import hyperdb, date, password

DEBUG=os.environ.get('HYPERDBDEBUG', '')

#
# Now the database
#
class Database(hyperdb.Database):
    """A database for storing records containing flexible data types.

    Transaction stuff TODO:
        . check the timestamp of the class file and nuke the cache if it's
          modified. Do some sort of conflict checking on the dirty stuff.
        . perhaps detect write collisions (related to above)?

    """
    def __init__(self, storagelocator, journaltag=None):
        """Open a hyperdatabase given a specifier to some storage.

        The meaning of 'storagelocator' depends on the particular
        implementation of the hyperdatabase.  It could be a file name,
        a directory path, a socket descriptor for a connection to a
        database over the network, etc.

        The 'journaltag' is a token that will be attached to the journal
        entries for any edits done on the database.  If 'journaltag' is
        None, the database is opened in read-only mode: the Class.create(),
        Class.set(), and Class.retire() methods are disabled.
        """
        self.dir, self.journaltag = storagelocator, journaltag
        self.classes = {}
        self.cache = {}         # cache of nodes loaded or created
        self.dirtynodes = {}    # keep track of the dirty nodes by class
        self.newnodes = {}      # keep track of the new nodes by class
        self.transactions = []

    def __repr__(self):
        return '<back_anydbm instance at %x>'%id(self) 

    #
    # Classes
    #
    def __getattr__(self, classname):
        """A convenient way of calling self.getclass(classname)."""
        if self.classes.has_key(classname):
            if DEBUG:
                print '__getattr__', (self, classname)
            return self.classes[classname]
        raise AttributeError, classname

    def addclass(self, cl):
        if DEBUG:
            print 'addclass', (self, cl)
        cn = cl.classname
        if self.classes.has_key(cn):
            raise ValueError, cn
        self.classes[cn] = cl

    def getclasses(self):
        """Return a list of the names of all existing classes."""
        if DEBUG:
            print 'getclasses', (self,)
        l = self.classes.keys()
        l.sort()
        return l

    def getclass(self, classname):
        """Get the Class object representing a particular class.

        If 'classname' is not a valid class name, a KeyError is raised.
        """
        if DEBUG:
            print 'getclass', (self, classname)
        return self.classes[classname]

    #
    # Class DBs
    #
    def clear(self):
        '''Delete all database contents
        '''
        if DEBUG:
            print 'clear', (self,)
        for cn in self.classes.keys():
            for type in 'nodes', 'journals':
                path = os.path.join(self.dir, 'journals.%s'%cn)
                if os.path.exists(path):
                    os.remove(path)
                elif os.path.exists(path+'.db'):    # dbm appends .db
                    os.remove(path+'.db')

    def getclassdb(self, classname, mode='r'):
        ''' grab a connection to the class db that will be used for
            multiple actions
        '''
        if DEBUG:
            print 'getclassdb', (self, classname, mode)
        return self._opendb('nodes.%s'%classname, mode)

    def _opendb(self, name, mode):
        '''Low-level database opener that gets around anydbm/dbm
           eccentricities.
        '''
        if DEBUG:
            print '_opendb', (self, name, mode)
        # determine which DB wrote the class file
        db_type = ''
        path = os.path.join(os.getcwd(), self.dir, name)
        if os.path.exists(path):
            db_type = whichdb.whichdb(path)
            if not db_type:
                raise hyperdb.DatabaseError, "Couldn't identify database type"
        elif os.path.exists(path+'.db'):
            # if the path ends in '.db', it's a dbm database, whether
            # anydbm says it's dbhash or not!
            db_type = 'dbm'

        # new database? let anydbm pick the best dbm
        if not db_type:
            if DEBUG:
                print "_opendb anydbm.open(%r, 'n')"%path
            return anydbm.open(path, 'n')

        # open the database with the correct module
        try:
            dbm = __import__(db_type)
        except ImportError:
            raise hyperdb.DatabaseError, \
                "Couldn't open database - the required module '%s'"\
                "is not available"%db_type
        if DEBUG:
            print "_opendb %r.open(%r, %r)"%(db_type, path, mode)
        return dbm.open(path, mode)

    #
    # Nodes
    #
    def addnode(self, classname, nodeid, node):
        ''' add the specified node to its class's db
        '''
        if DEBUG:
            print 'addnode', (self, classname, nodeid, node)
        self.newnodes.setdefault(classname, {})[nodeid] = 1
        self.cache.setdefault(classname, {})[nodeid] = node
        self.savenode(classname, nodeid, node)

    def setnode(self, classname, nodeid, node):
        ''' change the specified node
        '''
        if DEBUG:
            print 'setnode', (self, classname, nodeid, node)
        self.dirtynodes.setdefault(classname, {})[nodeid] = 1
        # can't set without having already loaded the node
        self.cache[classname][nodeid] = node
        self.savenode(classname, nodeid, node)

    def savenode(self, classname, nodeid, node):
        ''' perform the saving of data specified by the set/addnode
        '''
        if DEBUG:
            print 'savenode', (self, classname, nodeid, node)
        self.transactions.append((self._doSaveNode, (classname, nodeid, node)))

    def getnode(self, classname, nodeid, db=None):
        ''' add the specified node to its class's db
        '''
        if DEBUG:
            print 'getnode', (self, classname, nodeid, cldb)
        # try the cache
        cache = self.cache.setdefault(classname, {})
        if cache.has_key(nodeid):
            return cache[nodeid]

        # get from the database and save in the cache
        if db is None:
            db = self.getclassdb(classname)
        if not db.has_key(nodeid):
            raise IndexError, nodeid
        res = marshal.loads(db[nodeid])
        cache[nodeid] = res
        return res

    def hasnode(self, classname, nodeid, db=None):
        ''' add the specified node to its class's db
        '''
        if DEBUG:
            print 'hasnode', (self, classname, nodeid, cldb)
        # try the cache
        cache = self.cache.setdefault(classname, {})
        if cache.has_key(nodeid):
            return 1

        # not in the cache - check the database
        if db is None:
            db = self.getclassdb(classname)
        res = db.has_key(nodeid)
        return res

    def countnodes(self, classname, db=None):
        if DEBUG:
            print 'countnodes', (self, classname, cldb)
        # include the new nodes not saved to the DB yet
        count = len(self.newnodes.get(classname, {}))

        # and count those in the DB
        if db is None:
            db = self.getclassdb(classname)
        count = count + len(db.keys())
        return count

    def getnodeids(self, classname, db=None):
        if DEBUG:
            print 'getnodeids', (self, classname, db)
        # start off with the new nodes
        res = self.newnodes.get(classname, {}).keys()

        if db is None:
            db = self.getclassdb(classname)
        res = res + db.keys()
        return res

    #
    # Journal
    #
    def addjournal(self, classname, nodeid, action, params):
        ''' Journal the Action
        'action' may be:

            'create' or 'set' -- 'params' is a dictionary of property values
            'link' or 'unlink' -- 'params' is (classname, nodeid, propname)
            'retire' -- 'params' is None
        '''
        if DEBUG:
            print 'addjournal', (self, classname, nodeid, action, params)
        self.transactions.append((self._doSaveJournal, (classname, nodeid,
            action, params)))

    def getjournal(self, classname, nodeid):
        ''' get the journal for id
        '''
        if DEBUG:
            print 'getjournal', (self, classname, nodeid)
        # attempt to open the journal - in some rare cases, the journal may
        # not exist
        try:
            db = self._opendb('journals.%s'%classname, 'r')
        except anydbm.error, error:
            if str(error) == "need 'c' or 'n' flag to open new db": return []
            elif error.args[0] != 2: raise
            return []
        journal = marshal.loads(db[nodeid])
        res = []
        for entry in journal:
            (nodeid, date_stamp, self.journaltag, action, params) = entry
            date_obj = date.Date(date_stamp)
            res.append((nodeid, date_obj, self.journaltag, action, params))
        return res


    #
    # Basic transaction support
    #
    def commit(self):
        ''' Commit the current transactions.
        '''
        if DEBUG:
            print 'commit', (self,)
        # lock the DB
        for method, args in self.transactions:
            # TODO: optimise this, duh!
            method(*args)
        # unlock the DB

        # all transactions committed, back to normal
        self.cache = {}
        self.dirtynodes = {}
        self.newnodes = {}
        self.transactions = []

    def _doSaveNode(self, classname, nodeid, node):
        if DEBUG:
            print '_doSaveNode', (self, classname, nodeid, node)
        db = self.getclassdb(classname, 'c')
        # now save the marshalled data
        db[nodeid] = marshal.dumps(node)
        db.close()

    def _doSaveJournal(self, classname, nodeid, action, params):
        if DEBUG:
            print '_doSaveJournal', (self, classname, nodeid, action, params)
        entry = (nodeid, date.Date().get_tuple(), self.journaltag, action,
            params)
        db = self._opendb('journals.%s'%classname, 'c')
        if db.has_key(nodeid):
            s = db[nodeid]
            l = marshal.loads(db[nodeid])
            l.append(entry)
        else:
            l = [entry]
        db[nodeid] = marshal.dumps(l)
        db.close()

    def rollback(self):
        ''' Reverse all actions from the current transaction.
        '''
        if DEBUG:
            print 'rollback', (self, )
        self.cache = {}
        self.dirtynodes = {}
        self.newnodes = {}
        self.transactions = []

#
#$Log: back_anydbm.py,v $
#Revision 1.17  2001/12/14 23:42:57  richard
#yuck, a gdbm instance tests false :(
#I've left the debugging code in - it should be removed one day if we're ever
#_really_ anal about performace :)
#
#Revision 1.16  2001/12/12 03:23:14  richard
#Cor blimey this anydbm/whichdb stuff is yecchy. Turns out that whichdb
#incorrectly identifies a dbm file as a dbhash file on my system. This has
#been submitted to the python bug tracker as issue #491888:
#https://sourceforge.net/tracker/index.php?func=detail&aid=491888&group_id=5470&atid=105470
#
#Revision 1.15  2001/12/12 02:30:51  richard
#I fixed the problems with people whose anydbm was using the dbm module at the
#backend. It turns out the dbm module modifies the file name to append ".db"
#and my check to determine if we're opening an existing or new db just
#tested os.path.exists() on the filename. Well, no longer! We now perform a
#much better check _and_ cope with the anydbm implementation module changing
#too!
#I also fixed the backends __init__ so only ImportError is squashed.
#
#Revision 1.14  2001/12/10 22:20:01  richard
#Enabled transaction support in the bsddb backend. It uses the anydbm code
#where possible, only replacing methods where the db is opened (it uses the
#btree opener specifically.)
#Also cleaned up some change note generation.
#Made the backends package work with pydoc too.
#
#Revision 1.13  2001/12/02 05:06:16  richard
#. We now use weakrefs in the Classes to keep the database reference, so
#  the close() method on the database is no longer needed.
#  I bumped the minimum python requirement up to 2.1 accordingly.
#. #487480 ] roundup-server
#. #487476 ] INSTALL.txt
#
#I also cleaned up the change message / post-edit stuff in the cgi client.
#There's now a clearly marked "TODO: append the change note" where I believe
#the change note should be added there. The "changes" list will obviously
#have to be modified to be a dict of the changes, or somesuch.
#
#More testing needed.
#
#Revision 1.12  2001/12/01 07:17:50  richard
#. We now have basic transaction support! Information is only written to
#  the database when the commit() method is called. Only the anydbm
#  backend is modified in this way - neither of the bsddb backends have been.
#  The mail, admin and cgi interfaces all use commit (except the admin tool
#  doesn't have a commit command, so interactive users can't commit...)
#. Fixed login/registration forwarding the user to the right page (or not,
#  on a failure)
#
#Revision 1.11  2001/11/21 02:34:18  richard
#Added a target version field to the extended issue schema
#
#Revision 1.10  2001/10/09 23:58:10  richard
#Moved the data stringification up into the hyperdb.Class class' get, set
#and create methods. This means that the data is also stringified for the
#journal call, and removes duplication of code from the backends. The
#backend code now only sees strings.
#
#Revision 1.9  2001/10/09 07:25:59  richard
#Added the Password property type. See "pydoc roundup.password" for
#implementation details. Have updated some of the documentation too.
#
#Revision 1.8  2001/09/29 13:27:00  richard
#CGI interfaces now spit up a top-level index of all the instances they can
#serve.
#
#Revision 1.7  2001/08/12 06:32:36  richard
#using isinstance(blah, Foo) now instead of isFooType
#
#Revision 1.6  2001/08/07 00:24:42  richard
#stupid typo
#
#Revision 1.5  2001/08/07 00:15:51  richard
#Added the copyright/license notice to (nearly) all files at request of
#Bizar Software.
#
#Revision 1.4  2001/07/30 01:41:36  richard
#Makes schema changes mucho easier.
#
#Revision 1.3  2001/07/25 01:23:07  richard
#Added the Roundup spec to the new documentation directory.
#
#Revision 1.2  2001/07/23 08:20:44  richard
#Moved over to using marshal in the bsddb and anydbm backends.
#roundup-admin now has a "freshen" command that'll load/save all nodes (not
# retired - mod hyperdb.Class.list() so it lists retired nodes)
#
#

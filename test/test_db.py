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
# $Id: test_db.py,v 1.22 2002/05/21 05:52:11 richard Exp $ 

import unittest, os, shutil

from roundup.hyperdb import String, Password, Link, Multilink, Date, \
    Interval, Class, DatabaseError
from roundup.roundupdb import FileClass
from roundup import date, password

def setupSchema(db, create):
    status = Class(db, "status", name=String())
    status.setkey("name")
    if create:
        status.create(name="unread")
        status.create(name="in-progress")
        status.create(name="testing")
        status.create(name="resolved")
    Class(db, "user", username=String(), password=Password())
    Class(db, "issue", title=String(), status=Link("status"),
        nosy=Multilink("user"), deadline=Date(), foo=Interval())
    FileClass(db, "file", name=String(), type=String())
    db.commit()

class MyTestCase(unittest.TestCase):
    def tearDown(self):
        if os.path.exists('_test_dir'):
            shutil.rmtree('_test_dir')

class config:
    DATABASE='_test_dir'
    MAILHOST = 'localhost'
    MAIL_DOMAIN = 'fill.me.in.'
    INSTANCE_NAME = 'Roundup issue tracker'
    ISSUE_TRACKER_EMAIL = 'issue_tracker@%s'%MAIL_DOMAIN
    ISSUE_TRACKER_WEB = 'http://some.useful.url/'
    ADMIN_EMAIL = 'roundup-admin@%s'%MAIL_DOMAIN
    FILTER_POSITION = 'bottom'      # one of 'top', 'bottom', 'top and bottom'
    ANONYMOUS_ACCESS = 'deny'       # either 'deny' or 'allow'
    ANONYMOUS_REGISTER = 'deny'     # either 'deny' or 'allow'
    MESSAGES_TO_AUTHOR = 'no'       # either 'yes' or 'no'
    EMAIL_SIGNATURE_POSITION = 'bottom'

class anydbmDBTestCase(MyTestCase):
    def setUp(self):
        from roundup.backends import anydbm
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        self.db = anydbm.Database(config, 'test')
        setupSchema(self.db, 1)
        self.db2 = anydbm.Database(config, 'test')
        setupSchema(self.db2, 0)

    def testChanges(self):
        self.db.issue.create(title="spam", status='1')
        self.db.issue.create(title="eggs", status='2')
        self.db.issue.create(title="ham", status='4')
        self.db.issue.create(title="arguments", status='2')
        self.db.issue.create(title="abuse", status='1')
        self.db.issue.addprop(fixer=Link("user"))
        props = self.db.issue.getprops()
        keys = props.keys()
        keys.sort()
        self.assertEqual(keys, ['deadline', 'fixer', 'foo', 'id', 'nosy',
            'status', 'title'])
        self.db.issue.set('5', status='2')
        self.db.issue.get('5', "status")

        a = self.db.issue.get('5', "deadline")
        self.db.issue.set('5', deadline=date.Date())
        b = self.db.issue.get('5', "deadline")
        self.db.commit()
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, date.Date('1970-1-1 00:00:00'))
        self.db.issue.set('5', deadline=date.Date())

        a = self.db.issue.get('5', "foo")
        self.db.issue.set('5', foo=date.Interval('-1d'))
        self.assertNotEqual(a, self.db.issue.get('5', "foo"))

        self.db.status.get('2', "name")
        self.db.issue.get('5', "title")
        self.db.issue.find(status = self.db.status.lookup("in-progress"))
        self.db.commit()
        self.db.issue.history('5')
        self.db.status.history('1')
        self.db.status.history('2')

    def testSerialisation(self):
        self.db.issue.create(title="spam", status='1',
            deadline=date.Date(), foo=date.Interval('-1d'))
        self.db.commit()
        assert isinstance(self.db.issue.get('1', 'deadline'), date.Date)
        assert isinstance(self.db.issue.get('1', 'foo'), date.Interval)
        self.db.user.create(username="fozzy",
            password=password.Password('t. bear'))
        self.db.commit()
        assert isinstance(self.db.user.get('1', 'password'), password.Password)

    def testTransactions(self):
        # remember the number of items we started
        num_issues = len(self.db.issue.list())
        num_files = self.db.numfiles()
        self.db.issue.create(title="don't commit me!", status='1')
        self.assertNotEqual(num_issues, len(self.db.issue.list()))
        self.db.rollback()
        self.assertEqual(num_issues, len(self.db.issue.list()))
        self.db.issue.create(title="please commit me!", status='1')
        self.assertNotEqual(num_issues, len(self.db.issue.list()))
        self.db.commit()
        self.assertNotEqual(num_issues, len(self.db.issue.list()))
        self.db.rollback()
        self.assertNotEqual(num_issues, len(self.db.issue.list()))
        self.db.file.create(name="test", type="text/plain", content="hi")
        self.db.rollback()
        self.assertEqual(num_files, self.db.numfiles())
        for i in range(10):
            self.db.file.create(name="test", type="text/plain", 
                    content="hi %d"%(i))
            self.db.commit()
        num_files2 = self.db.numfiles()
        self.assertNotEqual(num_files, num_files2)
        self.db.file.create(name="test", type="text/plain", content="hi")
        self.db.rollback()
        self.assertNotEqual(num_files, self.db.numfiles())
        self.assertEqual(num_files2, self.db.numfiles())

    def testExceptions(self):
        # this tests the exceptions that should be raised
        ar = self.assertRaises

        #
        # class create
        #
        # string property
        ar(TypeError, self.db.status.create, name=1)
        # invalid property name
        ar(KeyError, self.db.status.create, foo='foo')
        # key name clash
        ar(ValueError, self.db.status.create, name='unread')
        # invalid link index
        ar(IndexError, self.db.issue.create, title='foo', status='bar')
        # invalid link value
        ar(ValueError, self.db.issue.create, title='foo', status=1)
        # invalid multilink type
        ar(TypeError, self.db.issue.create, title='foo', status='1',
            nosy='hello')
        # invalid multilink index type
        ar(ValueError, self.db.issue.create, title='foo', status='1',
            nosy=[1])
        # invalid multilink index
        ar(IndexError, self.db.issue.create, title='foo', status='1',
            nosy=['10'])

        #
        # class get
        #
        # invalid node id
        ar(IndexError, self.db.status.get, '10', 'name')
        # invalid property name
        ar(KeyError, self.db.status.get, '2', 'foo')

        #
        # class set
        #
        # invalid node id
        ar(IndexError, self.db.issue.set, '1', name='foo')
        # invalid property name
        ar(KeyError, self.db.status.set, '1', foo='foo')
        # string property
        ar(TypeError, self.db.status.set, '1', name=1)
        # key name clash
        ar(ValueError, self.db.status.set, '2', name='unread')
        # set up a valid issue for me to work on
        self.db.issue.create(title="spam", status='1')
        # invalid link index
        ar(IndexError, self.db.issue.set, '6', title='foo', status='bar')
        # invalid link value
        ar(ValueError, self.db.issue.set, '6', title='foo', status=1)
        # invalid multilink type
        ar(TypeError, self.db.issue.set, '6', title='foo', status='1',
            nosy='hello')
        # invalid multilink index type
        ar(ValueError, self.db.issue.set, '6', title='foo', status='1',
            nosy=[1])
        # invalid multilink index
        ar(IndexError, self.db.issue.set, '6', title='foo', status='1',
            nosy=['10'])

    def testJournals(self):
        self.db.issue.addprop(fixer=Link("user", do_journal='yes'))
        self.db.user.create(username="mary")
        self.db.user.create(username="pete")
        self.db.issue.create(title="spam", status='1')
        self.db.commit()

        # journal entry for issue create
        journal = self.db.getjournal('issue', '1')
        self.assertEqual(1, len(journal))
        (nodeid, date_stamp, journaltag, action, params) = journal[0]
        self.assertEqual(nodeid, '1')
        self.assertEqual(journaltag, 'test')
        self.assertEqual(action, 'create')
        keys = params.keys()
        keys.sort()
        self.assertEqual(keys, ['deadline', 'fixer', 'foo', 'nosy', 
            'status', 'title'])
        self.assertEqual(None,params['deadline'])
        self.assertEqual(None,params['fixer'])
        self.assertEqual(None,params['foo'])
        self.assertEqual([],params['nosy'])
        self.assertEqual('1',params['status'])
        self.assertEqual('spam',params['title'])

        # journal entry for link
        journal = self.db.getjournal('user', '1')
        self.assertEqual(1, len(journal))
        self.db.issue.set('1', fixer='1')
        self.db.commit()
        journal = self.db.getjournal('user', '1')
        self.assertEqual(2, len(journal))
        (nodeid, date_stamp, journaltag, action, params) = journal[1]
        self.assertEqual('1', nodeid)
        self.assertEqual('test', journaltag)
        self.assertEqual('link', action)
        self.assertEqual(('issue', '1', 'fixer'), params)

        # journal entry for unlink
        self.db.issue.set('1', fixer='2')
        self.db.commit()
        journal = self.db.getjournal('user', '1')
        self.assertEqual(3, len(journal))
        (nodeid, date_stamp, journaltag, action, params) = journal[2]
        self.assertEqual('1', nodeid)
        self.assertEqual('test', journaltag)
        self.assertEqual('unlink', action)
        self.assertEqual(('issue', '1', 'fixer'), params)

    def testPack(self):
        self.db.issue.create(title="spam", status='1')
        self.db.commit()
        self.db.issue.set('1', status='2')
        self.db.commit()
        self.db.issue.set('1', status='3')
        self.db.commit()
        pack_before = date.Date(". + 1d")
        self.db.pack(pack_before)
        journal = self.db.getjournal('issue', '1')
        self.assertEqual(2, len(journal))

    def testRetire(self):
        pass

    def testIDGeneration(self):
        id1 = self.db.issue.create(title="spam", status='1')
        id2 = self.db2.issue.create(title="eggs", status='2')
        self.assertNotEqual(id1, id2)


class anydbmReadOnlyDBTestCase(MyTestCase):
    def setUp(self):
        from roundup.backends import anydbm
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        db = anydbm.Database(config, 'test')
        setupSchema(db, 1)
        self.db = anydbm.Database(config)
        setupSchema(self.db, 0)
        self.db2 = anydbm.Database(config, 'test')
        setupSchema(self.db2, 0)

    def testExceptions(self):
        # this tests the exceptions that should be raised
        ar = self.assertRaises

        # this tests the exceptions that should be raised
        ar(DatabaseError, self.db.status.create, name="foo")
        ar(DatabaseError, self.db.status.set, '1', name="foo")
        ar(DatabaseError, self.db.status.retire, '1')


class bsddbDBTestCase(anydbmDBTestCase):
    def setUp(self):
        from roundup.backends import bsddb
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        self.db = bsddb.Database(config, 'test')
        setupSchema(self.db, 1)
        self.db2 = bsddb.Database(config, 'test')
        setupSchema(self.db2, 0)

class bsddbReadOnlyDBTestCase(anydbmReadOnlyDBTestCase):
    def setUp(self):
        from roundup.backends import bsddb
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        db = bsddb.Database(config, 'test')
        setupSchema(db, 1)
        self.db = bsddb.Database(config)
        setupSchema(self.db, 0)
        self.db2 = bsddb.Database(config, 'test')
        setupSchema(self.db2, 0)


class bsddb3DBTestCase(anydbmDBTestCase):
    def setUp(self):
        from roundup.backends import bsddb3
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        self.db = bsddb3.Database(config, 'test')
        setupSchema(self.db, 1)
        self.db2 = bsddb3.Database(config, 'test')
        setupSchema(self.db2, 0)

class bsddb3ReadOnlyDBTestCase(anydbmReadOnlyDBTestCase):
    def setUp(self):
        from roundup.backends import bsddb3
        # remove previous test, ignore errors
        if os.path.exists(config.DATABASE):
            shutil.rmtree(config.DATABASE)
        os.makedirs(config.DATABASE + '/files')
        db = bsddb3.Database(config, 'test')
        setupSchema(db, 1)
        self.db = bsddb3.Database(config)
        setupSchema(self.db, 0)
        self.db2 = bsddb3.Database(config, 'test')
        setupSchema(self.db2, 0)


def suite():
    l = [
         unittest.makeSuite(anydbmDBTestCase, 'test'),
         unittest.makeSuite(anydbmReadOnlyDBTestCase, 'test')
    ]

    try:
        import bsddb
        l.append(unittest.makeSuite(bsddbDBTestCase, 'test'))
        l.append(unittest.makeSuite(bsddbReadOnlyDBTestCase, 'test'))
    except:
        print 'bsddb module not found, skipping bsddb DBTestCase'

    try:
        import bsddb3
        l.append(unittest.makeSuite(bsddb3DBTestCase, 'test'))
        l.append(unittest.makeSuite(bsddb3ReadOnlyDBTestCase, 'test'))
    except:
        print 'bsddb3 module not found, skipping bsddb3 DBTestCase'

    return unittest.TestSuite(l)

#
# $Log: test_db.py,v $
# Revision 1.22  2002/05/21 05:52:11  richard
# Well whadya know, bsddb3 works again.
# The backend is implemented _exactly_ the same as bsddb - so there's no
# using its transaction or locking support. It'd be nice to use those some
# day I suppose.
#
# Revision 1.21  2002/04/15 23:25:15  richard
# . node ids are now generated from a lockable store - no more race conditions
#
# We're using the portalocker code by Jonathan Feinberg that was contributed
# to the ASPN Python cookbook. This gives us locking across Unix and Windows.
#
# Revision 1.20  2002/04/03 05:54:31  richard
# Fixed serialisation problem by moving the serialisation step out of the
# hyperdb.Class (get, set) into the hyperdb.Database.
#
# Also fixed htmltemplate after the showid changes I made yesterday.
#
# Unit tests for all of the above written.
#
# Revision 1.19  2002/02/25 14:34:31  grubert
#  . use blobfiles in back_anydbm which is used in back_bsddb.
#    change test_db as dirlist does not work for subdirectories.
#    ATTENTION: blobfiles now creates subdirectories for files.
#
# Revision 1.18  2002/01/22 07:21:13  richard
# . fixed back_bsddb so it passed the journal tests
#
# ... it didn't seem happy using the back_anydbm _open method, which is odd.
# Yet another occurrance of whichdb not being able to recognise older bsddb
# databases. Yadda yadda. Made the HYPERDBDEBUG stuff more sane in the
# process.
#
# Revision 1.17  2002/01/22 05:06:09  rochecompaan
# We need to keep the last 'set' entry in the journal to preserve
# information on 'activity' for nodes.
#
# Revision 1.16  2002/01/21 16:33:20  rochecompaan
# You can now use the roundup-admin tool to pack the database
#
# Revision 1.15  2002/01/19 13:16:04  rochecompaan
# Journal entries for link and multilink properties can now be switched on
# or off.
#
# Revision 1.14  2002/01/16 07:02:57  richard
#  . lots of date/interval related changes:
#    - more relaxed date format for input
#
# Revision 1.13  2002/01/14 02:20:15  richard
#  . changed all config accesses so they access either the instance or the
#    config attriubute on the db. This means that all config is obtained from
#    instance_config instead of the mish-mash of classes. This will make
#    switching to a ConfigParser setup easier too, I hope.
#
# At a minimum, this makes migration a _little_ easier (a lot easier in the
# 0.5.0 switch, I hope!)
#
# Revision 1.12  2001/12/17 03:52:48  richard
# Implemented file store rollback. As a bonus, the hyperdb is now capable of
# storing more than one file per node - if a property name is supplied,
# the file is called designator.property.
# I decided not to migrate the existing files stored over to the new naming
# scheme - the FileClass just doesn't specify the property name.
#
# Revision 1.11  2001/12/10 23:17:20  richard
# Added transaction tests to test_db
#
# Revision 1.10  2001/12/03 21:33:39  richard
# Fixes so the tests use commit and not close
#
# Revision 1.9  2001/12/02 05:06:16  richard
# . We now use weakrefs in the Classes to keep the database reference, so
#   the close() method on the database is no longer needed.
#   I bumped the minimum python requirement up to 2.1 accordingly.
# . #487480 ] roundup-server
# . #487476 ] INSTALL.txt
#
# I also cleaned up the change message / post-edit stuff in the cgi client.
# There's now a clearly marked "TODO: append the change note" where I believe
# the change note should be added there. The "changes" list will obviously
# have to be modified to be a dict of the changes, or somesuch.
#
# More testing needed.
#
# Revision 1.8  2001/10/09 07:25:59  richard
# Added the Password property type. See "pydoc roundup.password" for
# implementation details. Have updated some of the documentation too.
#
# Revision 1.7  2001/08/29 06:23:59  richard
# Disabled the bsddb3 module entirely in the unit testing. See CHANGES for
# details.
#
# Revision 1.6  2001/08/07 00:24:43  richard
# stupid typo
#
# Revision 1.5  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.4  2001/07/30 03:45:56  richard
# Added more DB to test_db. Can skip tests where imports fail.
#
# Revision 1.3  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.2  2001/07/29 04:09:20  richard
# Added the fabricated property "id" to all hyperdb classes.
#
# Revision 1.1  2001/07/27 06:55:07  richard
# moving tests -> test
#
# Revision 1.7  2001/07/27 06:26:43  richard
# oops - wasn't deleting the test dir after the read-only tests
#
# Revision 1.6  2001/07/27 06:23:59  richard
# consistency
#
# Revision 1.5  2001/07/27 06:23:09  richard
# Added some new hyperdb tests to make sure we raise the right exceptions.
#
# Revision 1.4  2001/07/25 04:34:31  richard
# Added id and log to tests files...
#
#
# vim: set filetype=python ts=4 sw=4 et si

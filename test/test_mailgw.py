#
# Copyright (c) 2001 Richard Jones, richard@bofh.asn.au.
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# $Id: test_mailgw.py,v 1.17 2002/05/02 07:56:34 richard Exp $

import unittest, cStringIO, tempfile, os, shutil, errno, imp, sys, difflib

from roundup.mailgw import MailGW
from roundup import init, instance

# TODO: make this output only enough equal lines for context, not all of
# them
class DiffHelper:
    def compareStrings(self, s2, s1):
        '''Note the reversal of s2 and s1 - difflib.SequenceMatcher wants
           the first to be the "original" but in the calls in this file,
           the second arg is the original. Ho hum.
        '''
        if s1 == s2:
            return
        # under python2.1 we allow a difference of one trailing empty line.
        if sys.version_info[0:2] == (2,1):
            if s1+'\n' == s2:
                return
        
        l1=s1.split('\n')
        l2=s2.split('\n')
        s = difflib.SequenceMatcher(None, l1, l2)
        res = ['Generated message not correct (diff follows):']
        for value, s1s, s1e, s2s, s2e in s.get_opcodes():
            if value == 'equal':
                for i in range(s1s, s1e):
                    res.append('  %s'%l1[i])
            elif value == 'delete':
                for i in range(s1s, s1e):
                    res.append('- %s'%l1[i])
            elif value == 'insert':
                for i in range(s2s, s2e):
                    res.append('+ %s'%l2[i])
            elif value == 'replace':
                for i, j in zip(range(s1s, s1e), range(s2s, s2e)):
                    res.append('- %s'%l1[i])
                    res.append('+ %s'%l2[j])

        raise AssertionError, '\n'.join(res)

class MailgwTestCase(unittest.TestCase, DiffHelper):
    count = 0
    schema = 'classic'
    def setUp(self):
        MailgwTestCase.count = MailgwTestCase.count + 1
        self.dirname = '_test_%s'%self.count
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno not in (errno.ENOENT, errno.ESRCH): raise
        # create the instance
        init.init(self.dirname, self.schema, 'anydbm', 'sekrit')
        # check we can load the package
        self.instance = instance.open(self.dirname)
        # and open the database
        self.db = self.instance.open('sekrit')
        self.db.user.create(username='Chef', address='chef@bork.bork.bork')
        self.db.user.create(username='richard', address='richard@test')
        self.db.user.create(username='mary', address='mary@test')
        self.db.user.create(username='john', address='john@test',
            alternate_addresses='jondoe@test\njohn.doe@test')

    def tearDown(self):
        if os.path.exists(os.environ['SENDMAILDEBUG']):
            os.remove(os.environ['SENDMAILDEBUG'])
        try:
            shutil.rmtree(self.dirname)
        except OSError, error:
            if error.errno not in (errno.ENOENT, errno.ESRCH): raise

    def testNewIssue(self):
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: Chef <chef@bork.bork.bork
To: issue_tracker@fill.me.in.
Cc: richard@test
Message-Id: <dummy_test_message_id>
Subject: [issue] Testing...

This is a test submission of a new issue.
''')
        handler = self.instance.MailGW(self.instance, self.db)
        nodeid = handler.main(message)
        if os.path.exists(os.environ['SENDMAILDEBUG']):
            error = open(os.environ['SENDMAILDEBUG']).read()
            self.assertEqual('no error', error)
        self.assertEqual(self.db.issue.get(nodeid, 'nosy'), ['2', '3'])

    def testNewIssueNosy(self):
        self.instance.ADD_AUTHOR_TO_NOSY = 'yes'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: Chef <chef@bork.bork.bork
To: issue_tracker@fill.me.in.
Cc: richard@test
Message-Id: <dummy_test_message_id>
Subject: [issue] Testing...

This is a test submission of a new issue.
''')
        handler = self.instance.MailGW(self.instance, self.db)
        nodeid = handler.main(message)
        if os.path.exists(os.environ['SENDMAILDEBUG']):
            error = open(os.environ['SENDMAILDEBUG']).read()
            self.assertEqual('no error', error)
        self.assertEqual(self.db.issue.get(nodeid, 'nosy'), ['2', '3'])

    def testAlternateAddress(self):
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: John Doe <john.doe@test>
To: issue_tracker@fill.me.in.
Message-Id: <dummy_test_message_id>
Subject: [issue] Testing...

This is a test submission of a new issue.
''')
        userlist = self.db.user.list()
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)
        if os.path.exists(os.environ['SENDMAILDEBUG']):
            error = open(os.environ['SENDMAILDEBUG']).read()
            self.assertEqual('no error', error)
        self.assertEqual(userlist, self.db.user.list(),
            "user created when it shouldn't have been")

    def testNewIssueNoClass(self):
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: Chef <chef@bork.bork.bork
To: issue_tracker@fill.me.in.
Cc: richard@test
Message-Id: <dummy_test_message_id>
Subject: Testing...

This is a test submission of a new issue.
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)
        if os.path.exists(os.environ['SENDMAILDEBUG']):
            error = open(os.environ['SENDMAILDEBUG']).read()
            self.assertEqual('no error', error)

    def testNewIssueAuthMsg(self):
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: Chef <chef@bork.bork.bork
To: issue_tracker@fill.me.in.
Message-Id: <dummy_test_message_id>
Subject: [issue] Testing... [nosy=mary; assignedto=richard]

This is a test submission of a new issue.
''')
        handler = self.instance.MailGW(self.instance, self.db)
        # TODO: fix the damn config - this is apalling
        self.db.config.MESSAGES_TO_AUTHOR = 'yes'
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, mary@test, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, mary@test, richard@test
From: Chef <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


New submission from Chef <chef@bork.bork.bork>:

This is a test submission of a new issue.


----------
assignedto: richard
messages: 1
nosy: mary, Chef, richard
status: unread
title: Testing...
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')

    # BUG
    # def testMultipart(self):
    #         '''With more than one part'''
    #        see MultipartEnc tests: but if there is more than one part
    #        we return a multipart/mixed and the boundary contains
    #        the ip address of the test machine. 

    # BUG should test some binary attamchent too.

    def testFollowup(self):
        self.testNewIssue()
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: richard <richard@test>
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing... [assignedto=mary; nosy=john]

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, mary@test, john@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, mary@test, john@test
From: richard <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


richard <richard@test> added the comment:

This is a followup


----------
assignedto:  -> mary
nosy: +mary, john
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')

    def testFollowup2(self):
        self.testNewIssue()
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: mary <mary@test>
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a second followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)
        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, richard@test
From: mary <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


mary <mary@test> added the comment:

This is a second followup


----------
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')

    def testFollowupTitleMatch(self):
        self.testNewIssue()
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: richard <richard@test>
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: Re: Testing... [assignedto=mary; nosy=john]

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, mary@test, john@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, mary@test, john@test
From: richard <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


richard <richard@test> added the comment:

This is a followup


----------
assignedto:  -> mary
nosy: +mary, john
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')

    def testFollowupNosyAuthor(self):
        self.testNewIssue()
        self.instance.ADD_AUTHOR_TO_NOSY = 'yes'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: john@test
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, richard@test
From: john <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


john <john@test> added the comment:

This is a followup


----------
nosy: +john
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________

''')

    def testFollowupNosyRecipients(self):
        self.testNewIssue()
        self.instance.ADD_RECIPIENTS_TO_NOSY = 'yes'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: richard@test
To: issue_tracker@fill.me.in.
Cc: john@test
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork
From: richard <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


richard <richard@test> added the comment:

This is a followup


----------
nosy: +john
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________

''')

    def testFollowupNosyAuthorAndCopy(self):
        self.testNewIssue()
        self.instance.ADD_AUTHOR_TO_NOSY = 'yes'
        self.db.config.MESSAGES_TO_AUTHOR = 'yes'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: john@test
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: john@test, chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: john@test, chef@bork.bork.bork, richard@test
From: john <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


john <john@test> added the comment:

This is a followup


----------
nosy: +john
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________

''')

    def testFollowupNoNosyAuthor(self):
        self.testNewIssue()
        self.instance.ADD_AUTHOR_TO_NOSY = 'no'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: john@test
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, richard@test
From: john <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


john <john@test> added the comment:

This is a followup


----------
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________

''')

    def testFollowupNoNosyRecipients(self):
        self.testNewIssue()
        self.instance.ADD_RECIPIENTS_TO_NOSY = 'no'
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: richard@test
To: issue_tracker@fill.me.in.
Cc: john@test
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...

This is a followup
''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)

        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork
From: richard <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


richard <richard@test> added the comment:

This is a followup


----------
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________

''')

    def testEnc01(self):
        self.testNewIssue()
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: mary <mary@test>
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...
Content-Type: text/plain;
        charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

A message with encoding (encoded oe =F6)

''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)
        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, richard@test
From: mary <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


mary <mary@test> added the comment:

A message with encoding (encoded oe =F6)

----------
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')


    def testMultipartEnc01(self):
        self.testNewIssue()
        message = cStringIO.StringIO('''Content-Type: text/plain;
  charset="iso-8859-1"
From: mary <mary@test>
To: issue_tracker@fill.me.in.
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
Subject: [issue1] Testing...
Content-Type: multipart/mixed;
        boundary="----_=_NextPart_000_01"

This message is in MIME format. Since your mail reader does not understand
this format, some or all of this message may not be legible.

------_=_NextPart_000_01
Content-Type: text/plain;
        charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

A message with first part encoded (encoded oe =F6)

''')
        handler = self.instance.MailGW(self.instance, self.db)
        handler.main(message)
        self.compareStrings(open(os.environ['SENDMAILDEBUG']).read(),
'''FROM: roundup-admin@fill.me.in.
TO: chef@bork.bork.bork, richard@test
Content-Type: text/plain
Subject: [issue1] Testing...
To: chef@bork.bork.bork, richard@test
From: mary <issue_tracker@fill.me.in.>
Reply-To: Roundup issue tracker <issue_tracker@fill.me.in.>
MIME-Version: 1.0
Message-Id: <followup_dummy_id>
In-Reply-To: <dummy_test_message_id>
X-Roundup-Name: Roundup issue tracker
Content-Transfer-Encoding: quoted-printable


mary <mary@test> added the comment:

A message with first part encoded (encoded oe =F6)

----------
status: unread -> chatting
___________________________________________________
"Roundup issue tracker" <issue_tracker@fill.me.in.>
http://some.useful.url/issue1
___________________________________________________
''')

class ExtMailgwTestCase(MailgwTestCase):
    schema = 'extended'

def suite():
    l = [unittest.makeSuite(MailgwTestCase),
         unittest.makeSuite(ExtMailgwTestCase, 'test')
    ]
    return unittest.TestSuite(l)


#
# $Log: test_mailgw.py,v $
# Revision 1.17  2002/05/02 07:56:34  richard
# . added option to automatically add the authors and recipients of messages
#   to the nosy lists with the options ADD_AUTHOR_TO_NOSY (default 'new') and
#   ADD_RECIPIENTS_TO_NOSY (default 'new'). These settings emulate the current
#   behaviour. Setting them to 'yes' will add the author/recipients to the nosy
#   on messages that create issues and followup messages.
# . added missing documentation for a few of the config option values
#
# Revision 1.16  2002/03/19 21:58:11  grubert
#  . for python2.1 test_mailgw compareString allows an extra trailing empty line (for quopri.
#
# Revision 1.15  2002/03/19 06:37:00  richard
# Made the email checking spit out a diff - much easier to spot the problem!
#
# Revision 1.14  2002/03/18 18:32:00  rochecompaan
# All messages sent to the nosy list are now encoded as quoted-printable.
#
# Revision 1.13  2002/02/15 07:08:45  richard
#  . Alternate email addresses are now available for users. See the MIGRATION
#    file for info on how to activate the feature.
#
# Revision 1.12  2002/02/15 00:13:38  richard
#  . #503204 ] mailgw needs a default class
#     - partially done - the setting of additional properties can wait for a
#       better configuration system.
#
# Revision 1.11  2002/02/14 23:38:12  richard
# Fixed the unit tests for the mailgw re: the x-roundup-name header.
# Also made the test runner more user-friendly:
#   ./run_tests            - detect all tests in test/test_<name>.py and run them
#   ./run_tests <name>     - run only test/test_<name>.py
# eg ./run_tests mailgw    - run the mailgw test from test/test_mailgw.py
#
# Revision 1.10  2002/02/12 08:08:55  grubert
#  . Clean up mail handling, multipart handling.
#
# Revision 1.9  2002/02/05 14:15:29  grubert
#  . respect encodings in non multipart messages.
#
# Revision 1.8  2002/02/04 09:40:21  grubert
#  . add test for multipart messages with first part being encoded.
#
# Revision 1.7  2002/01/22 11:54:45  rochecompaan
# Fixed status change in mail gateway.
#
# Revision 1.6  2002/01/21 10:05:48  rochecompaan
# Feature:
#  . the mail gateway now responds with an error message when invalid
#    values for arguments are specified for link or multilink properties
#  . modified unit test to check nosy and assignedto when specified as
#    arguments
#
# Fixed:
#  . fixed setting nosy as argument in subject line
#
# Revision 1.5  2002/01/15 00:12:40  richard
# #503340 ] creating issue with [asignedto=p.ohly]
#
# Revision 1.4  2002/01/14 07:12:15  richard
# removed file writing from tests...
#
# Revision 1.3  2002/01/14 02:20:15  richard
#  . changed all config accesses so they access either the instance or the
#    config attriubute on the db. This means that all config is obtained from
#    instance_config instead of the mish-mash of classes. This will make
#    switching to a ConfigParser setup easier too, I hope.
#
# At a minimum, this makes migration a _little_ easier (a lot easier in the
# 0.5.0 switch, I hope!)
#
# Revision 1.2  2002/01/11 23:22:29  richard
#  . #502437 ] rogue reactor and unittest
#    in short, the nosy reactor was modifying the nosy list. That code had
#    been there for a long time, and I suspsect it was there because we
#    weren't generating the nosy list correctly in other places of the code.
#    We're now doing that, so the nosy-modifying code can go away from the
#    nosy reactor.
#
# Revision 1.1  2002/01/02 02:31:38  richard
# Sorry for the huge checkin message - I was only intending to implement #496356
# but I found a number of places where things had been broken by transactions:
#  . modified ROUNDUPDBSENDMAILDEBUG to be SENDMAILDEBUG and hold a filename
#    for _all_ roundup-generated smtp messages to be sent to.
#  . the transaction cache had broken the roundupdb.Class set() reactors
#  . newly-created author users in the mailgw weren't being committed to the db
#
# Stuff that made it into CHANGES.txt (ie. the stuff I was actually working
# on when I found that stuff :):
#  . #496356 ] Use threading in messages
#  . detectors were being registered multiple times
#  . added tests for mailgw
#  . much better attaching of erroneous messages in the mail gateway
#
#
#
#
# vim: set filetype=python ts=4 sw=4 et si

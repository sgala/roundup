# $Id: config.py,v 1.5 2001/07/19 06:27:07 anthonybaxter Exp $

ROUNDUP_HOME=MAIL_DOMAIN=MAILHOST=None

try:
    from localconfig import *
except ImportError:
    localconfig = None

import os

# This is the root directory for roundup
if not ROUNDUP_HOME:
    ROUNDUP_HOME='/home/httpd/html/roundup'

# The SMTP mail host that roundup will use to send mail
if not MAILHOST:
    MAILHOST = 'localhost'

# The domain name used for email addresses.
if not MAIL_DOMAIN:
    MAIL_DOMAIN = 'bizarsoftware.com.au'

# This is the directory that the database is going to be stored in
DATABASE = os.path.join(ROUNDUP_HOME, 'db')

# The email address that mail to roundup should go to
ISSUE_TRACKER_EMAIL = 'issue_tracker@%s'%MAIL_DOMAIN

# The email address that roundup will complain to if it runs into trouble
ADMIN_EMAIL = 'roundup-admin@%s'%MAIL_DOMAIN

# Somewhere for roundup to log stuff internally sent to stdout or stderr
LOG = os.path.join(ROUNDUP_HOME, 'roundup.log')

del os

#
# $Log: config.py,v $
# Revision 1.5  2001/07/19 06:27:07  anthonybaxter
# fixing (manually) the (dollarsign)Log(dollarsign) entries caused by
# my using the magic (dollarsign)Id(dollarsign) and (dollarsign)Log(dollarsign)
# strings in a commit message. I'm a twonk.
#
# Also broke the help string in two.
#
# Revision 1.4  2001/07/19 05:52:22  anthonybaxter
# Added CVS keywords Id and Log to all python files.
#
#


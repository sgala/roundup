
#
# TRACKER SCHEMA
#

# Class automatically gets these properties:
#   creation = Date()
#   activity = Date()
#   creator = Link('user')
#   actor = Link('user')

# Priorities
pri = Class(db, "priority",
                name=String(),
                order=Number())
pri.setkey("name")

# Statuses
stat = Class(db, "status",
                name=String(),
                order=Number())
stat.setkey("name")

# Keywords
keyword = Class(db, "keyword",
                name=String())
keyword.setkey("name")

# User-defined saved searches
query = Class(db, "query",
                klass=String(),
                name=String(),
                url=String(),
                private_for=Link('user'))

# add any additional database schema configuration here

user = Class(db, "user",
                username=String(),
                password=Password(),
                address=String(),
                realname=String(),
                phone=String(),
                organisation=String(),
                alternate_addresses=String(),
                queries=Multilink('query'),
                roles=String(),     # comma-separated string of Role names
                timezone=String())
user.setkey("username")

# FileClass automatically gets this property in addition to the Class ones:
#   content = String()    [saved to disk in <tracker home>/db/files/]
msg = FileClass(db, "msg",
                author=Link("user", do_journal='no'),
                recipients=Multilink("user", do_journal='no'),
                date=Date(),
                summary=String(),
                files=Multilink("file"),
                messageid=String(),
                inreplyto=String())

file = FileClass(db, "file",
                name=String(),
                type=String())

# IssueClass automatically gets these properties in addition to the Class ones:
#   title = String()
#   messages = Multilink("msg")
#   files = Multilink("file")
#   nosy = Multilink("user")
#   superseder = Multilink("issue")
issue = IssueClass(db, "issue",
                assignedto=Link("user"),
                topic=Multilink("keyword"),
                priority=Link("priority"),
                status=Link("status"))

#
# TRACKER SECURITY SETTINGS
#
# See the configuration and customisation document for information
# about security setup.

#
# REGULAR USERS
#
# Give the regular users access to the web and email interface
p = db.security.getPermission('Web Access')
db.security.addPermissionToRole('User', p)
p = db.security.getPermission('Email Access')
db.security.addPermissionToRole('User', p)

# Assign the access and edit Permissions for issue, file and message
# to regular users now
for cl in 'issue', 'file', 'msg', 'query', 'keyword':
    p = db.security.getPermission('View', cl)
    db.security.addPermissionToRole('User', p)
    p = db.security.getPermission('Edit', cl)
    db.security.addPermissionToRole('User', p)
    p = db.security.getPermission('Create', cl)
    db.security.addPermissionToRole('User', p)
for cl in 'priority', 'status':
    p = db.security.getPermission('View', cl)
    db.security.addPermissionToRole('User', p)

# May users view other user information? Comment these lines out
# if you don't want them to
p = db.security.getPermission('View', 'user')
db.security.addPermissionToRole('User', p)

# Users should be able to edit their own details. Note that this
# permission is limited to only the situation where the Viewed or
# Edited item is their own.
def own_record(db, userid, itemid):
    '''Determine whether the userid matches the item being accessed.'''
    return userid == itemid
p = db.security.addPermission(name='View', klass='user', check=own_record,
    description="User is allowed to view their own user details")
p = db.security.addPermission(name='Edit', klass='user', check=own_record,
    description="User is allowed to edit their own user details")
db.security.addPermissionToRole('User', p)

#
# ANONYMOUS USER PERMISSIONS
#
# Let anonymous users access the web interface. Note that almost all
# trackers will need this Permission. The only situation where it's not
# required is in a tracker that uses an HTTP Basic Authenticated front-end.
p = db.security.getPermission('Web Access')
db.security.addPermissionToRole('Anonymous', p)

# Let anonymous users access the email interface (note that this implies
# that they will be registered automatically, hence they will need the
# "Create" user Permission below)
p = db.security.getPermission('Email Access')
db.security.addPermissionToRole('Anonymous', p)

# Assign the appropriate permissions to the anonymous user's Anonymous
# Role. Choices here are:
# - Allow anonymous users to register
p = db.security.getPermission('Create', 'user')
db.security.addPermissionToRole('Anonymous', p)

# Allow anonymous users access to view issues (and the related, linked
# information)
for cl in 'issue', 'file', 'msg', 'keyword', 'priority', 'status':
    p = db.security.getPermission('View', cl)
    db.security.addPermissionToRole('Anonymous', p)

# [OPTIONAL]
# Allow anonymous users access to create or edit "issue" items (and the
# related file and message items)
#for cl in 'issue', 'file', 'msg':
#   p = db.security.getPermission('Create', cl)
#   db.security.addPermissionToRole('Anonymous', p)
#   p = db.security.getPermission('Edit', cl)
#   db.security.addPermissionToRole('Anonymous', p)


# vim: set filetype=python sts=4 sw=4 et si :
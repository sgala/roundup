#! /usr/bin/env python
# $Id: load_tracker.py,v 1.3 2004/04/22 22:17:34 richard Exp $

'''
Usage: %s <tracker home> <N>

Load up the indicated tracker with N issues and N/100 users.
'''

import sys, os, random
from roundup import instance

# open the instance
if len(sys.argv) < 2:
    print "Error: Not enough arguments"
    print __doc__.strip()%(sys.argv[0], username)
    sys.exit(1)
tracker_home = sys.argv[1]
N = int(sys.argv[2])

# open the tracker
tracker = instance.open(tracker_home)
db = tracker.open('admin')

priorities = db.priority.list()
statuses = db.status.list()

names = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 
'theta', 'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi',
'rho']

titles = '''Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
Duis nibh purus, bibendum sed, condimentum ut, bibendum ut, risus.
Fusce pede enim, nonummy sit amet, dapibus a, blandit eget, metus.
Nulla risus.
Vivamus tincidunt.
Donec consequat convallis quam.
Sed convallis vehicula felis.
Aliquam laoreet, dui quis pharetra vehicula, magna justo.
Euismod felis, eu adipiscing eros metus id tortor.
Suspendisse et turpis.
Aenean non felis.
Nam egestas eros.
Integer tellus quam, mattis ac, vestibulum sed, egestas quis, mauris.
Nulla tincidunt diam sit amet dui.
Nam odio mauris, dignissim vitae, eleifend eu, consectetuer id, risus.
Suspendisse potenti.
Donec tincidunt.
Vestibulum gravida.
Fusce luctus, neque id mattis fringilla, purus pede sodales pede.
Quis ultricies urna odio sed orci.'''.splitlines()

try:
    M = N/100
    print
    for i in range(M):
        print '\ruser', i*100./M,
        sys.stdout.flush()
        db.user.create(username=names[i%17]+str(i/17))

    users = db.user.list()
    users.remove(db.user.lookup('anonymous'))
    print

    # now create the issues
    for i in range(N):
        print '\rissue', i*100./N,
        sys.stdout.flush()
        db.issue.create(
            title=random.choice(titles),
            priority=random.choice(priorities),
            status=random.choice(statuses),
            assignedto=random.choice(users))
        if i%10:
            db.commit()
    print

    db.commit()
finally:
    db.close()

# vim: set filetype=python ts=4 sw=4 et si

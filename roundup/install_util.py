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
# $Id: install_util.py,v 1.7 2001/11/24 01:00:13 jhermann Exp $

__doc__ = """
Support module to generate and check fingerprints of installed files.
"""

import os, sha, shutil

# ".filter", ".index", ".item", ".newitem" are roundup-specific
sgml_file_types = [".xml", ".ent", ".html", ".filter", ".index", ".item", ".newitem"]
hash_file_types = [".py", ".sh", ".conf", ".cgi", '']
slast_file_types = [".css"]

digested_file_types = sgml_file_types + hash_file_types + slast_file_types


def checkDigest(filename):
    """Read file, check for valid fingerprint, return TRUE if ok"""
    # open and read file
    inp = open(filename, "r")
    lines = inp.readlines()
    inp.close()

    # get fingerprint from last line
    if lines[-1][:6] == "#SHA: ":
        # handle .py/.sh comment
        fingerprint = lines[-1][6:].strip()
    elif lines[-1][:10] == "<!-- SHA: ":
        # handle xml/html files
        fingerprint = lines[-1][10:]
        fingerprint = fingerprint.replace('-->', '')
        fingerprint = fingerprint.strip()
    elif lines[-1][:8] == "/* SHA: ":
        # handle css files
        fingerprint = lines[-1][8:]
        fingerprint = fingerprint.replace('*/', '')
        fingerprint = fingerprint.strip()
    else:
        return 0
    del lines[-1]

    # calculate current digest
    digest = sha.new()
    for line in lines:
        digest.update(line)

    # compare current to stored digest
    return fingerprint == digest.hexdigest()


class DigestFile:
    """ A class that you can use like open() and that calculates
        and writes a SHA digest to the target file.
    """

    def __init__(self, filename):
        self.filename = filename
        self.digest = sha.new()
        self.file = open(self.filename, "w")

    def write(self, data):
        self.file.write(data)
        self.digest.update(data)

    def close(self):
        file, ext = os.path.splitext(self.filename)

        if ext in sgml_file_types:
            self.file.write("<!-- SHA: %s -->\n" % (self.digest.hexdigest(),))
        elif ext in hash_file_types:
            self.file.write("#SHA: %s\n" % (self.digest.hexdigest(),))
        elif ext in slast_file_types:
            self.file.write("/* SHA: %s */\n" % (self.digest.hexdigest(),))

        self.file.close()


def copyDigestedFile(src, dst, copystat=1):
    """ Copy data from `src` to `dst`, adding a fingerprint to `dst`.
        If `copystat` is true, the file status is copied, too
        (like shutil.copy2).
    """
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    dummy, ext = os.path.splitext(src)
    if ext not in digested_file_types:
        if copystat:
            return shutil.copy2(src, dst)
        else:
            return shutil.copyfile(src, dst)

    fsrc = None
    fdst = None
    try:
        fsrc = open(src, 'r')
        fdst = DigestFile(dst)
        shutil.copyfileobj(fsrc, fdst)
    finally:
        if fdst: fdst.close()
        if fsrc: fsrc.close()

    if copystat: shutil.copystat(src, dst)


def test():
    import sys

    testdata = open(sys.argv[0], 'r').read()

    for ext in digested_file_types:
        testfile = "__digest_test" + ext

        out = DigestFile(testfile)
        out.write(testdata)
        out.close()

        assert checkDigest(testfile), "digest ok w/o modification"

        mod = open(testfile, 'r+')
        mod.seek(0)
        mod.write('# changed!')
        mod.close()

        assert not checkDigest(testfile), "digest fails after modification"

        os.remove(testfile)


if __name__ == '__main__':
    test()

#
# $Log: install_util.py,v $
# Revision 1.7  2001/11/24 01:00:13  jhermann
# Added .newitem extension
#
# Revision 1.6  2001/11/22 15:46:42  jhermann
# Added module docstrings to all modules.
#
# Revision 1.5  2001/11/12 23:17:38  jhermann
# Code using copyDigestedFile() that passes unit tests
#
# Revision 1.4  2001/11/12 23:14:40  jhermann
# Copy function, and proper handling of unknown file types
#
# Revision 1.3  2001/11/12 22:38:48  richard
# bleah typo
#
# Revision 1.2  2001/11/12 22:37:13  richard
# Handle all the various file formats in roundup
#
# Revision 1.1  2001/11/12 22:26:32  jhermann
# Added install utils (digest calculation)
#


#!/usr/bin/python
# lame_vcs_abstraction.py:
#
# Licensed under the new-BSD license (http://www.opensource.org/licenses/bsd-license.php)
# Copyright (C) 2010 Red Hat, Inc.
# Written by Colin Walters <walters@verbum.org>

# Feel free to replace the bits here with something better...

import os
import sys
import re
import urlparse
import getopt
import subprocess
import shutil
import hashlib

class Vcs(object):
    def __init__(self, parsedurl):
        self._parsed_url = parsedurl
        # Deliberately drop params/query
        self._nonfragment_url_string = urlparse.urlunparse((parsedurl.scheme,
                                                            parsedurl.netloc,
                                                            parsedurl.path,
                                                            '', '', ''))
        self._branch = self._parsed_url.fragment
        
    def get_url(self):
        return self._parsed_url
        
    def checkout(self, destdir):
        """Retrieve a new copy of the source tree, saving as destdir"""
        raise Exception("not implemented")
        
    def update(self, directory):
        """Update directory from the latest upstream"""
        raise Exception("not implemented")
        
    def get_scheme(self):
        return self._parsed_url.scheme
        
    def get_id(self, directory):
        raise Exception("not implemented")
        
    def get_abbreviated_id(self, directory):
        raise Exception("not implemented")
        
    def switch_to_revision(self, directory, newid):
        """Switch the working tree to the revision identified by newid.
If newid is None, then switch to the latest upstream."""
        raise Exception("not implemented")
        
    def _vcs_exec(self, *args, **kwargs):
        print "Running: %r" % (args[0], )
        if not 'stdout' in kwargs:
            kwargs['stdout'] = sys.stdout
        if not 'stderr' in kwargs:
            kwargs['stderr'] = sys.stderr
        subprocess.check_call(*args, **kwargs)
        
    @classmethod
    def new_from_spec(cls, spec):
        """See http://maven.apache.org/scm/scm-url-format.html ; we use this format,
        but without the "scm:" prefix."""
        # Hack for backwards compatibility
        if spec.startswith('git://'):
            (vcstype, url) = ('git', spec)
        else:
            (vcstype, url) = spec.split(':', 1)
        orig = urlparse.urlsplit(url)
        # We want to support fragments, even if the URL type isn't recognized.  So change the
        # scheme to http temporarily.
        temp = urlparse.urlunsplit(('http', orig.netloc, orig.path, orig.query, orig.fragment))
        new = urlparse.urlsplit(temp)
        combined = urlparse.SplitResult(orig.scheme, new.netloc, new.path, new.query, new.fragment)
        if vcstype == 'git':
            return GitVcs(combined)
        
class GitVcs(Vcs):
    vcstype = "git"

    def checkout(self, destdir):
        self._vcs_exec(['git', 'clone', '--depth=1', self._nonfragment_url_string, destdir])
        if self._branch:
            self._vcs_exec(['git', 'checkout', self._branch], cwd=destdir)
        
    def update(self, directory):
        if self._branch:
            self._vcs_exec(['git', 'checkout', self._branch], cwd=directory)
        self._vcs_exec(['git', 'pull', '-r'], cwd=directory)
        
    def get_commit_as_patch(self, directory, commitid, destfile):
        f = open(destfile, 'w')
        self._vcs_exec(['git', 'format-patch', '--stdout', commitid + '^..' + commitid],
                        cwd=directory, stdout=f, stderr=sys.stderr)
        f.close()   
        
    def get_id(self, directory):
        output = subprocess.Popen(['git', 'show', '--format=%H'], stdout=subprocess.PIPE, cwd=directory).communicate()[0]
        return output.split('\n')[0]
        
    def get_abbreviated_id(self, directory):
        full_id = self.get_id(directory)
        return full_id[0:8]
        
    def switch_to_revision(self, directory, newid):
        if newid is None:
            newid = self._branch or 'master'
        self._vcs_exec(['git', 'checkout', newid], cwd=directory)

    def get_commit_summary_as_filename(self, directory, commitid):
        output = subprocess.Popen(['git', 'show', '--format=%f', commitid], stdout=subprocess.PIPE, cwd=directory).communicate()[0]
        return output.split('\n')[0]

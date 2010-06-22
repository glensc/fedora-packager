#!/usr/bin/python
# build_intelligence.py: Introspect source tarballs and discover build characteristics
#
# Licensed under the new-BSD license (http://www.opensource.org/licenses/bsd-license.php)
# Copyright (C) 2010 Red Hat, Inc.
# Written by Colin Walters <walters@verbum.org>


import os
import sys
import re
           
class BuildSystem(object):
    def __init__(self, directory):
        self._directory = directory
        
    @classmethod
    def new_from_directory(cls, directory):
        autogen_path = os.path.join(directory, 'autogen.sh')
        if os.path.exists(autogen_path):
            return AutogenAutotools(directory)
        if os.path.exists(os.path.join(directory, 'Makefile.am')):
            return Autotools(directory)
            
    def get_bootstrap_buildrequires(self):
        return []
        
    def get_substitutions(self):
        return []

    def _file_matches(self, filename, pattern):
        matches = self._file_matches_many(filename, (pattern, ))
        if matches:
            return True
        return False

    def _file_matches_many(self, filename, patterns):
        """Given an input set of 2-tuples in @patterns (key, pattern)
and filename @filename, return the set of keys which match any line in
the contents of the file."""
        if not os.path.isabs(filename):
            filename = os.path.join(self._directory, filename)
        regexps = {}
        for (key, pattern) in patterns:
            regexps[key] = re.compile(pattern)
        f = open(filename)
        matches = set()
        try:
            for line in f:
                matched = []
                for key, regexp in regexps.iteritems():
                    if regexp.search(line):
                        matched.append(key)
                for key in matched:
                    del regexps[key]
                    matches.add(key)
                if not regexps:
                    break
        finally:
            f.close()
        return matches 
        
class Autotools(BuildSystem):
    def get_bootstrap_buildrequires(self):
        return ['libtool', 'automake', 'autoconf']
        
    def get_substitutions(self):
        return [(re.compile('^%configure'), 'autoreconf -f -i\n%configure')]
        
class AutogenAutotools(Autotools):
    def __init__(self, directory):
        Autotools.__init__(self, directory)
        matches = self._file_matches_many('autogen.sh', 
                                          (('gnome-common', r'gnome-autogen\.sh'),
                                           ('gtk-doc', r'gtkdocize')))
        if 'gnome-common' in matches:
            matches.add('gtk-doc')
        self._bootstrap_requires = matches

    def get_bootstrap_buildrequires(self):
        bootstrap = super(AutogenAutotools, self).get_bootstrap_buildrequires()
        for match in self._bootstrap_requires:
            bootstrap.append(match)
        return bootstrap
        
    def get_substitutions(self):
        # We'll configure twice with this, but oh well.  Need this in RPM.
        subs = [(re.compile('^%configure'), './autogen.sh && %configure')]
        # If we're not building from a tarball, we need to ensure gtk-doc
        # gets built.
        if 'gtk-doc' in self._bootstrap_requires:
            subs.append((re.compile('(%configure.*)--disable-gtk-doc'), r'\1'))
            subs.append((re.compile('(%configure.*)'), r'\1 --enable-gtk-doc'))
        return subs 
        

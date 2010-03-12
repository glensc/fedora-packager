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
        
class Autotools(BuildSystem):
    def get_bootstrap_buildrequires(self):
        return ['libtool', 'automake', 'autoconf']
        
    def get_substitutions(self):
        return [(re.compile('^%configure'), 'autoreconf -f -i\n%configure')]
        
class AutogenAutotools(Autotools):
    def get_bootstrap_buildrequires(self):
        bootstrap = super(AutogenAutotools, self).get_bootstrap_buildrequires()
        bootstrap.append('gnome-common')
        bootstrap.append('intltool')
        return bootstrap
        
    def get_substitutions(self):
        # We'll configure twice with this, but oh well.  Need this in RPM.
        return [(re.compile('^%configure'), './autogen.sh && %configure')]
        

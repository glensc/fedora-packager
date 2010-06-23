#!/usr/bin/python
# spec.py: Read and write RPM .spec files
#
# Licensed under the new-BSD license (http://www.opensource.org/licenses/bsd-license.php)
# Copyright (C) 2010 Red Hat, Inc.
# Written by Colin Walters <walters@verbum.org>

import os
import sys
import re
import urlparse
import getopt
import subprocess
import shutil
import hashlib

class Spec(object):
    # These two constants were cribbed from rpm-spec-mode.el.
    SECTIONS = ('%preamble', '%description', '%prep', '%setup',
                '%build', '%install', '%check', '%clean',
                '%changelog', '%files')
    SCRIPTS = ('%pre', '%post', '%preun', '%postun',
               '%trigger', '%triggerin', '%treiggerprein',
               '%triggerun', '%triggerpostun', '%pretrans',
               '%posttrans')
    def __init__(self, filename):
        self._filename = filename
        f = open(filename)
        self._lines = self._read_lines_joining_backslash(f) 
        f.close()
        self._saved = False
        self._append_buildrequires = []
        self._new_release = None
        self._source_dirname = None
        self._source_archivename = None
        self._substitutions = []
        # Map from section name (e.g. '%build') -> (list of functions)
        self._section_filters = {}
        self._added_patches = []

    def _read_lines_joining_backslash(self, f):
        lines = f.readlines()
        concat_line = None
        out_lines = []
        for line in lines:
            if line.endswith('\\\n'):
                if concat_line is None:
                    concat_line = line
                else:
                    concat_line += line[:-2]
            else:
                if concat_line:
                    out_lines.append(concat_line)
                    concat_line = None
                out_lines.append(line)    
        if concat_line:
            out_lines.append(concat_line)
        return out_lines 

    def get_name(self):
        return self._filename[:-5]
        
    def add_buildrequires(self, new_buildrequires):
        assert not self._saved
        current_buildrequires = self.get_key_allvalues('BuildRequires')
        new_buildrequires = filter(lambda x: x not in current_buildrequires, new_buildrequires)
        self._append_buildrequires = new_buildrequires
        
    def increment_release_snapshot(self, identifier):
        assert not self._saved
        cur_release = self.get_key('Release')
        release_has_dist = cur_release.endswith('%{?dist}')
        if release_has_dist:
            cur_release = cur_release[:-8]
        snapshot_release_re = re.compile(r'^([0-9]+)\.([0-9]+)\.')
        numeric_re = re.compile(r'^([0-9]+)$')
        match = snapshot_release_re.match(cur_release)
        if match:
            firstint = int(match.group(1))
            relint = int(match.group(2)) + 1
            new_release = '%d.%d.%s' % (firstint, relint, identifier)
        else:
            match = numeric_re.match(cur_release)
            if not match:
                raise ValueError("Can't handle Release value: %r" % (cur_release, ))
            new_release = '%s.0.%s' % (cur_release, identifier)
        if release_has_dist:
            new_release += '%{?dist}'
            
        self._new_release = new_release
        
    def set_source(self, dirname, archivename):
        assert not self._saved
        self._source_dirname = dirname
        self._source_archivename = archivename
        
    def add_section_filter(self, name, function):
        if not (name in self.SECTIONS or name in self.SCRIPTS):
            raise KeyError("Invalid section name %r" % (name, ))
        if name not in self._section_filters:
            self._section_filters[name] = []
        self._section_filters[name].append(function)

    def _line_is_section(self, line):
        for section in self.SECTIONS:
            if line.startswith(section):
                return True
        for section in self.SCRIPTS:
            if line.startswith(section):
                return True
        return False

    def _get_range_for_section(self, name):
        if not (name in self.SECTIONS or name in self.SCRIPTS):
            raise KeyError("Invalid section name %r" % (name, ))
        section_start = -1
        section_end = -1
        for i, line in enumerate(self._lines):
            if line.startswith(name):
                section_start = i
            elif section_start >= 0:
                if self._line_is_section(line):                
                    section_end = i
                    break
        if section_start >= 0:
            section_end = len(self._lines) - 1
        return (section_start, section_end)

    def replace_key_line(self, key, new_value, line):
        """Takes a line of the form "Release: 42  # foo" and replaces
the 42 with new_value, preserving the comment # foo."""
        comment = line.rfind('#')
        if comment >= 0:
            return '%s: %s %s\n' % (key, new_value, line[comment:])
        else:
            return '%s: %s\n' % (key, new_value)

    def add_patch(self, filename):
        patches = self.get_patches()
        if len(patches) == 0:
            patchnum = 0
        else:
            patchnums = map(lambda a: a[0], patches)
            patchnum = max(patchnums)
        self._added_patches.append(filename)
        
    def save(self):
        self._saved = True
        tmpname = self._filename + '.tmp'
        self.save_as(tmpname)
        os.rename(tmpname, self._filename)
        
    def save_as(self, new_filename):
        wrote_buildrequires = False
        output = open(new_filename, 'w')
        
        apply_patchmeta_at_line = -1
        apply_patch_apply_at_line = -1
        source_re = re.compile(r'^Source([0-9]*):')
        patch_re = re.compile(r'^Patch([0-9]+):')
        apply_re = re.compile(r'^%patch')
        highest_patchnum = -1

        output_lines = self._lines

        for i,line in enumerate(output_lines):
            match = patch_re.search(line)
            if match:
                apply_patchmeta_at_line = i
                highest_patchnum = int(match.group(1))
                continue
            match = source_re.search(line)
            if match:
                apply_patchmeta_at_line = i
                if highest_patchnum == -1:
                    highest_patchnum = 0
                continue
            if line.startswith('%setup'):
                apply_patch_apply_at_line = i + 1
                continue
            match = apply_re.search(line)
            if match:
                apply_patch_apply_at_line = i + 1
                continue
        if apply_patchmeta_at_line == -1:
            print "Error: Couldn't determine where to add Patch:"
            sys.exit(1)
        if apply_patch_apply_at_line == -1:
            print "Error: Couldn't determine where to add %patch"
            sys.exit(1)
        
        for section,filters in self._section_filters.iteritems():
            (start, end) = self._get_range_for_section(section)
            splices = []
            for i,line in enumerate(output_lines[start:end]):
                for f in filters:
                    result = f(line)
                    if result is not None:
                        output_lines[i] = line = f(line)

        for i,line in enumerate(output_lines):
            if i == apply_patchmeta_at_line:
                for pnum,patch in enumerate(self._added_patches):
                    output.write('Patch%d: %s\n' % (highest_patchnum + pnum + 1, patch))
            elif i == apply_patch_apply_at_line:
                for pnum,patch in enumerate(self._added_patches):
                    output.write('%%patch%d -p1\n' % (highest_patchnum + pnum + 1, ))
        
            if line.startswith('%setup') and self._source_dirname:  # This is dumb, need to automate this in RPM
                output.write('%%setup -q -n %s\n' % self._source_dirname)
            elif ':' in line:
                key, value = line.split(':', 1)
                if key == 'Release' and self._new_release:
                    output.write(self.replace_key_line(key, self._new_release, line))
                elif (line.startswith('Source0:') or line.startswith('Source:')) and self._source_archivename:
                    output.write(self.replace_key_line(key, self._source_archivename, line))
                elif key == 'BuildRequires' and not wrote_buildrequires:
                    output.write(line)
                    for req in self._append_buildrequires:
                        output.write('BuildRequires: %s\n' % req)
                    wrote_buildrequires = True
                else:
                    output.write(line)
            else:
                output.write(line)
                
        output.close()
        
    def get_patches(self):
        patchre = re.compile(r'^Patch([0-9]+):')
        patches = []
        for line in self._lines:
            match = patchre.search(line)
            if not match:
                continue
            patches.append((int(match.group(1)), line.split(':', 1)[1].strip()))
        return patches

    def get_version(self):
        return self.get_key('Version')
        
    def get_vcs(self):
        for line in self._lines:
            if line.startswith('#VCS:'):
                return line[5:].strip()
        raise ValueError("No such key #VCS in file %r" % (self._filename, ))
        
    def get_key(self, key):
        key = key + ':'
        for line in self._lines:
            if line.startswith(key):
                return line[len(key):].strip()
        raise ValueError("No such key %r in file %r" % (key, self._filename))
        
    def get_key_allvalues(self, key):
        key = key + ':'
        result = []
        for line in self._lines:
            if line.startswith(key):
                result.append(line[len(key):].strip())
        return result

    def __str__(self):
        return self._filename


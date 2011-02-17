#!/usr/bin/python
# fedpkg - a script to interact with the Fedora Packaging system
#
# Copyright (C) 2009 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import argparse
import os
import sys
import getpass
import logging
import xmlrpclib
import time
import random
import string
import re
import hashlib
import textwrap

# See/put non-standard python imports down in __main__.  This lets us
# generate the man page without needing extra stuff at build time.

# Define packages which belong to specific secondary arches
# This is ugly and should go away.  A better way to do this is to have a list
# of secondary arches, and then check the spec file for ExclusiveArch that
# is one of the secondary arches, and handle it accordingly.
SECONDARY_ARCH_PKGS = {'sparc': ['silo', 'prtconf', 'lssbus', 'afbinit',
                                 'piggyback', 'xorg-x11-drv-sunbw2',
                                 'xorg-x11-drv-suncg14', 'xorg-x11-drv-suncg3',
                                 'xorg-x11-drv-suncg6', 'xorg-x11-drv-sunffb',
                                 'xorg-x11-drv-sunleo', 'xorg-x11-drv-suntcx'],
                       'ppc': ['ppc64-utils', 'yaboot'],
                       'arm': []}

# Add a log filter class
class StdoutFilter(logging.Filter):

    def filter(self, record):
        # If the record level is 20 (INFO) or lower, let it through
        return record.levelno <= logging.INFO

# Add a simple function to print usage, for the 'help' command
def usage(args):
    parser.print_help()

def getuser(user=None):
    if user:
        return user
    else:
        return os.getlogin()

def check(args):
    # not implimented; Not planned
    log.warning('Not implimented yet, got %s' % args)

def clean(args):
    dry = False
    useignore = True
    if args.dry_run:
        dry = True
    if args.x:
        useignore = False
    try:
        return pyfedpkg.clean(dry, useignore)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not clean: %s' % e)
        sys.exit(1)

def clog(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.clog()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not generate clog: %s' % e)
        sys.exit(1)

def clone(args):
    user = None
    if not args.anonymous:
        # Doing a try doesn't really work since the fedora_cert library just
        # exits on error, but if that gets fixed this will work better.
        user = getuser(args.user)
    try:
        if args.branches:
            pyfedpkg.clone_with_dirs(args.module[0], user)
        else:
            pyfedpkg.clone(args.module[0], user, args.path, args.branch)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not clone: %s' % e)
        sys.exit(1)

def commit(args):
    mymodule = None
    if args.clog:
        try:
            mymodule = pyfedpkg.PackageModule(args.path, args.dist)
            mymodule.clog()
        except pyfedpkg.FedpkgError, e:
            log.error('coult not create clog: %s' % e)
            sys.exit(1)
        args.file = os.path.abspath(os.path.join(args.path, 'clog'))
    try:
        pyfedpkg.commit(args.path, args.message, args.file, args.files)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not commit: %s' % e)
        sys.exit(1)
    if args.tag:
        try:
            if not mymodule:
                mymodule = pyfedpkg.PackageModule(args.path, args.dist)
            tagname = mymodule.nvr
            pyfedpkg.add_tag(tagname, True, args.message, args.file)
        except pyfedpkg.FedpkgError, e:
            log.error('Coult not create a tag: %s' % e)
            sys.exit(1)
    if args.push:
        push(args)

def compile(args):
    arch = None
    short = False
    if args.arch:
        arch = args.arch
    if args.short_circuit:
        short = True
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.compile(arch=arch, short=short)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not compile: %s' % e)
        sys.exit(1)

def diff(args):
    try:
        return pyfedpkg.diff(args.path, args.cached, args.files)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not diff: %s' % e)
        sys.exit(1)

def export(args):
    # not implimented; not planned
    log.warning('Not implimented yet, got %s' % args)

def gimmespec(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        print(mymodule.spec)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get spec file: %s' % e)
        sys.exit(1)

def giturl(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        print(mymodule.giturl())
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get the giturl: %s' % e)
        sys.exit(1)

def import_srpm(args):
    # See if we need to create a module from scratch, and do so
    if args.create:
        log.warning('Not implimented yet.')
        sys.exit(0)
    if not args.create:
        try:
            uploadfiles = pyfedpkg.import_srpm(args.srpm, path=args.path)
            mymodule = pyfedpkg.PackageModule(args.path, args.dist)
            mymodule.upload(uploadfiles, replace=True)
        except pyfedpkg.FedpkgError, e:
            log.error('Could not import srpm: %s' % e)
            sys.exit(1)
        # replace this system call with a proper diff target when it is
        # readys
        pyfedpkg.diff(args.path, cached=True)
        print('--------------------------------------------')
        print("New content staged and new sources uploaded.")
        print("Commit if happy or revert with: git reset --hard HEAD")
    return

def install(args):
    arch = None
    short = False
    if args.arch:
        arch = args.arch
    if args.short_circuit:
        short = True
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.install(arch=arch, short=short)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not install: %s' % e)
        sys.exit(1)

def lint(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.lint(args.info)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not run rpmlint: %s' % e)
        sys.exit(1)

def local(args):
    arch = None
    if args.arch:
        arch = args.arch
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        if args.md5:
            return mymodule.local(arch=arch, hashtype='md5')
        else:
            return mymodule.local(arch=arch)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not build locally: %s' % e)
        sys.exit(1)

def new(args):
    try:
        print(pyfedpkg.new(args.path))
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get new changes: %s' % e)
        sys.exit(1)

def new_sources(args):
    # Check to see if the files passed exist
    for file in args.files:
        if not os.path.exists(file):
            log.error('File does not exist: %s' % file)
            sys.exit(1)
    user = getuser(args.user)
    passwd = getpass.getpass('Password for %s: ' % user)
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        mymodule.upload(args.files, replace=args.replace, user=user, passwd=passwd)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not upload new sources: %s' % e)
        sys.exit(1)
    print("Source upload succeeded. Don't forget to commit the .spec file")

def patch(args):
    # not implimented
    log.warning('Not implimented yet, got %s' % args)

def prep(args):
    arch = None
    if args.arch:
        arch = args.arch
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.prep(arch=arch)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not prep: %s' % e)
        sys.exit(1)

def pull(args):
    try:
        pyfedpkg.pull(path=args.path, rebase=args.rebase, norebase=args.no_rebase)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not pull: %s' % e)
        sys.exit(1)

def push(args):
    try:
        pyfedpkg.push(path=args.path)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not push: %s' % e)
        sys.exit(1)

def retire(args):
    try:
        pyfedpkg.retire(args.path, args.msg)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not retire package: %s' % e)
        sys.exit(1)
    if args.push:
        push()

def sources(args):
    try:
        pyfedpkg.sources(args.path, args.outdir)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not download sources: %s' % e)
        sys.exit(1)

def srpm(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        pyfedpkg.sources(args.path)
        if args.md5:
            mymodule.srpm('md5')
        else:
            mymodule.srpm()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not make an srpm: %s' % e)
        sys.exit(1)

def switch_branch(args):
    if args.branch:
        try:
            pyfedpkg.switch_branch(args.branch, args.path)
        except pyfedpkg.FedpkgError, e:
            log.error('Unable to switch to another branch: %s' % e)
            sys.exit(1)
    else:
        try:
            (locals, remotes) = pyfedpkg._list_branches(path=args.path)
        except pyfedpkg.FedpkgError, e:
            log.error('Unable to list branches: %s' % e)
            sys.exit(1)
        # This is some ugly stuff here, but trying to emulate
        # the way git branch looks
        locals = ['  %s  ' % branch for branch in locals]
        local_branch = pyfedpkg._find_branch(args.path)
        locals[locals.index('  %s  ' % local_branch)] = '* %s' % local_branch
        print('Locals:\n%s\nRemotes:\n  %s' %
              ('\n'.join(locals), '\n  '.join(remotes)))

def tag(args):
    if args.list:
        try:
            pyfedpkg.list_tag(args.tag)
        except pyfedpkg.FedpkgError, e:
            log.error('Could not create a list of the tag: %s' % e)
            sys.exit(1)
    elif args.delete:
        try:
            pyfedpkg.delete_tag(args.tag, args.path)
        except pyfedpkg.FedpkgError, e:
            log.error('Coult not delete tag: %s' % e)
            sys.exit(1)
    else:
        filename = args.file
        tagname = args.tag
        try:
            if not tagname or args.clog:
                mymodule = pyfedpkg.PackageModule(args.path, args.dist)
                if not tagname:
                    tagname = mymodule.nvr
                if clog:
                    mymodule.clog()
                    filename = 'clog'
            pyfedpkg.add_tag(tagname, args.force, args.message, filename)
        except pyfedpkg.FedpkgError, e:
            log.error('Coult not create a tag: %s' % e)
            sys.exit(1)

def unusedfedpatches(args):
    # not implimented; not planned
    log.warning('Not implimented yet, got %s' % args)

def unusedpatches(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        unused = mymodule.unused_patches()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get unused patches: %s' % e)
        sys.exit(1)
    print('\n'.join(unused))

def verify_files(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
        return mymodule.verify_files()
    except pyfedpkg.FedpkgError, e:
        log.error('Could not verify %%files list: %s' % e)
        sys.exit(1)

def verrel(args):
    try:
        mymodule = pyfedpkg.PackageModule(args.path, args.dist)
    except pyfedpkg.FedpkgError, e:
        log.error('Could not get ver-rel: %s' % e)
        sys.exit(1)
    print('%s-%s-%s' % (mymodule.module, mymodule.ver, mymodule.rel))


def parse_cmdline(generate_manpage = False):
    """Parse the command line"""

    # Create the parser object
    parser = argparse.ArgumentParser(description = 'Fedora Packaging utility',
                                     prog = 'fedpkg',
                                     epilog = "For detailed help pass " \
                                               "--help to a target")

    # Add top level arguments
    # Let people override the "distribution"
    parser.add_argument('--dist', default=None,
                        help='Override the distribution, eg f15 or el6')
    # Let somebody override the username found in fedora cert
    parser.add_argument('-u', '--user',
                        help = "Override the username found in the fedora cert")
    # Let the user define which path to look at instead of pwd
    parser.add_argument('--path', default = None,
                    help='Directory to interact with instead of current dir')
    # Verbosity
    parser.add_argument('-v', action = 'store_true',
                        help = 'Run with verbose debug output')
    parser.add_argument('-q', action = 'store_true',
                        help = 'Run quietly only displaying errors')

    # Add a subparsers object to use for the actions
    subparsers = parser.add_subparsers(title = 'Targets',
                                       description = 'These are valid commands you can ask fedpkg to do.')

    # Set up the various actions
    # Add help to -h and --help
    parser_help = subparsers.add_parser('help', help = 'Show usage')
    parser_help.set_defaults(command = usage)

    # check preps; not planned
    #parser_check = subparsers.add_parser('check',
    #                            help = 'Check test srpm preps on all arches')
    #parser_check.set_defaults(command = check)

    # clean things up
    parser_clean = subparsers.add_parser('clean',
                                         help = 'Remove untracked files',
                                         description = "This command can be \
                                         used to clean up your working \
                                         directory.  By default it will \
                                         follow .gitignore rules.")
    parser_clean.add_argument('--dry-run', '-n', action = 'store_true',
                              help = 'Perform a dry-run')
    parser_clean.add_argument('-x', action = 'store_true',
                              help = 'Do not follow .gitignore rules')
    parser_clean.set_defaults(command = clean)

    # Create a changelog stub
    parser_clog = subparsers.add_parser('clog',
                                        help = 'Make a clog file containing '
                                        'top changelog entry',
                                        description = 'This will create a \
                                        file named "clog" that contains the \
                                        latest rpm changelog entry. The \
                                        leading "- " text will be stripped.')
    parser_clog.set_defaults(command = clog)

    # clone take some options, and then passes the rest on to git
    parser_clone = subparsers.add_parser('clone',
                                         help = 'Clone and checkout a module',
                                         description = 'This command will \
                                         clone the named module from the \
                                         configured repository base URL.  \
                                         By default it will also checkout \
                                         the master branch for your working \
                                         copy.')
    # Allow an old style clone with subdirs for branches
    parser_clone.add_argument('--branches', '-B',
                              action = 'store_true',
                              help = 'Do an old style checkout with subdirs \
                              for branches')
    # provide a convenient way to get to a specific branch
    parser_clone.add_argument('--branch', '-b',
                              help = 'Check out a specific branch')
    # allow to clone without needing a account on the fedora buildsystem
    parser_clone.add_argument('--anonymous', '-a',
                              action = 'store_true',
                              help = 'Check out a branch anonymously')
    # store the module to be cloned
    parser_clone.add_argument('module', nargs = 1,
                              help = 'Name of the module to clone')
    parser_clone.set_defaults(command = clone)

    parser_co = subparsers.add_parser('co', parents = [parser_clone],
                                      conflict_handler = 'resolve',
                                      help = 'Alias for clone',
                                      description = 'This command will \
                                      clone the named module from the \
                                      configured repository base URL.  \
                                      By default it will also checkout \
                                      the master branch for your working \
                                      copy.')
    parser_co.set_defaults(command = clone)

    # commit stuff
    parser_commit = subparsers.add_parser('commit',
                                          help = 'Commit changes',
                                          description = 'This envokes a git \
                                          commit.  All tracked files with \
                                          changes will be committed unless \
                                          a specific file list is provided.  \
                                          $EDITOR will be used to generate a \
                                          changelog message unless one is \
                                          given to the command.  A push \
                                          can be done at the same time.')
    parser_commit.add_argument('-c', '--clog',
                               default = False,
                               action = 'store_true',
                               help = 'Generate the commit message from the Changelog section')
    parser_commit.add_argument('-t', '--tag',
                               default = False,
                               action = 'store_true',
                               help = 'Create a tag for this commit')
    parser_commit.add_argument('-m', '--message',
                               default = None,
                               help = 'Use the given <msg> as the commit message')
    parser_commit.add_argument('-F', '--file',
                               default = None,
                               help = 'Take the commit message from the given file')
    # allow one to commit /and/ push at the same time.
    parser_commit.add_argument('-p', '--push',
                               default = False,
                               action = 'store_true',
                               help = 'Commit and push as one action')
    # Allow a list of files to be committed instead of everything
    parser_commit.add_argument('files', nargs = '*',
                               default = [],
                               help = 'Optional list of specific files to commit')
    parser_commit.set_defaults(command = commit)

    parser_ci = subparsers.add_parser('ci', parents = [parser_commit],
                                      conflict_handler = 'resolve',
                                      help = 'Alias for commit',
                                      description = 'This envokes a git \
                                      commit.  All tracked files with \
                                      changes will be committed unless \
                                      a specific file list is provided.  \
                                      $EDITOR will be used to generate a \
                                      changelog message unless one is \
                                      given to the command.  A push \
                                      can be done at the same time.')
    parser_ci.set_defaults(command = commit)

    # compile locally
    parser_compile = subparsers.add_parser('compile',
                                           help = 'Local test rpmbuild compile',
                                           description = 'This command calls \
                                           rpmbuild to compile the source.  \
                                           By default the prep and configure \
                                           stages will be done as well, \
                                           unless the short-circuit option \
                                           is used.')
    parser_compile.add_argument('--arch', help = 'Arch to compile for')
    parser_compile.add_argument('--short-circuit', action = 'store_true',
                                help = 'short-circuit compile')
    parser_compile.set_defaults(command = compile)

    # export the module; not planned
    #parser_export = subparsers.add_parser('export',
    #                                      help = 'Create a clean export')
    #parser_export.set_defaults(command = export)

    # diff, should work mostly like git diff
    parser_diff = subparsers.add_parser('diff',
                                        help = 'Show changes between commits, '
                                        'commit and working tree, etc',
                                        description = 'Use git diff to show \
                                        changes that have been made to \
                                        tracked files.  By default cached \
                                        changes (changes that have been git \
                                        added) will not be shown.')
    parser_diff.add_argument('--cached', default = False,
                             action = 'store_true',
                             help = 'View staged changes')
    parser_diff.add_argument('files', nargs = '*',
                             default = [],
                             help = 'Optionally diff specific files')
    parser_diff.set_defaults(command = diff)

    # gimmespec takes an optional path argument, defaults to cwd
    parser_gimmespec = subparsers.add_parser('gimmespec',
                                             help = 'Print the spec file name')
    parser_gimmespec.set_defaults(command = gimmespec)

    # giturl
    parser_giturl = subparsers.add_parser('giturl',
                                          help = 'Print the git url for '
                                          'building',
                                          description = 'This will show you \
                                          which git URL would be used in a \
                                          build command.  It uses the git \
                                          hashsum of the HEAD of the current \
                                          branch (which may not be pushed).')
    parser_giturl.set_defaults(command = giturl)

    # Import content into a module
    parser_import_srpm = subparsers.add_parser('import',
                                               help = 'Import srpm content '
                                               'into a module',
                                               description = 'This will \
                                               extract sources, patches, and \
                                               the spec file from an srpm and \
                                               update the current module \
                                               accordingly.  It will import \
                                               to the current branch by \
                                               default.')
    parser_import_srpm.add_argument('--branch', '-b',
                                    help = 'Branch to import onto',
                                    default = 'devel')
    parser_import_srpm.add_argument('--create', '-c',
                                    help = 'Create a new local repo',
                                    action = 'store_true')
    parser_import_srpm.add_argument('srpm',
                                    help = 'Source rpm to import')
    parser_import_srpm.set_defaults(command = import_srpm)

    # install locally
    parser_install = subparsers.add_parser('install',
                                           help = 'Local test rpmbuild install',
                                           description = 'This will call \
                                           rpmbuild to run the install \
                                           section.  All leading sections \
                                           will be processed as well, unless \
                                           the short-circuit option is used.')
    parser_install.add_argument('--arch', help = 'Arch to install for')
    parser_install.add_argument('--short-circuit', action = 'store_true',
                                help = 'short-circuit install')
    parser_install.set_defaults(command = install)

    # rpmlint target
    parser_lint = subparsers.add_parser('lint',
                                        help = 'Run rpmlint against local '
                                        'build output')
    parser_lint.add_argument('--info', '-i',
                             default = False,
                             action = 'store_true',
                             help = 'Display explanations for reported messages')
    parser_lint.set_defaults(command = lint)

    # Build locally
    parser_local = subparsers.add_parser('local',
                                         help = 'Local test rpmbuild binary',
                                         description = 'Locally test run of \
                                         rpmbuild producing binary RPMs. The \
                                         rpmbuild output will be logged into a \
                                         file named \
                                         .build-%{version}-%{release}.log')
    parser_local.add_argument('--arch', help = 'Build for arch')
    # optionally define old style hashsums
    parser_local.add_argument('--md5', action = 'store_true',
                              help = 'Use md5 checksums (for older rpm hosts)')
    parser_local.set_defaults(command = local)

    # See what's different
    parser_new = subparsers.add_parser('new',
                                       help = 'Diff against last tag',
                                       description = 'This will use git to \
                                       show a diff of all the changes \
                                       (even uncommited changes) since the \
                                       last git tag was applied.')
    parser_new.set_defaults(command = new)

    # newsources target takes one or more files as input
    parser_newsources = subparsers.add_parser('new-sources',
                                              help = 'Upload new source files',
                                              description = 'This will upload \
                                              new source files to the \
                                              lookaside cache and remove \
                                              any existing files.  The \
                                              "sources" and .gitignore file \
                                              will be updated for the new \
                                              file(s).')
    parser_newsources.add_argument('files', nargs = '+')
    parser_newsources.set_defaults(command = new_sources, replace = True)

    # patch
    parser_patch = subparsers.add_parser('patch',
                                         help = 'Create and add a gendiff '
                                         'patch file')
    parser_patch.add_argument('--suffix')
    parser_patch.add_argument('--rediff', action = 'store_true',
                              help = 'Recreate gendiff file retaining comments')
    parser_patch.set_defaults(command = patch)

    # Prep locally
    parser_prep = subparsers.add_parser('prep',
                                        help = 'Local test rpmbuild prep',
                                        description = 'Use rpmbuild to "prep" \
                                        the sources (unpack the source \
                                        archive(s) and apply any patches.)')
    parser_prep.add_argument('--arch', help = 'Prep for a specific arch')
    parser_prep.set_defaults(command = prep)

    # Pull stuff
    parser_pull = subparsers.add_parser('pull',
                                        help = 'Pull changes from remote '
                                        'repository and update working copy.',
                                        description = 'This command uses git \
                                        to fetch remote changes and apply \
                                        them to the current working copy.  A \
                                        rebase option is available which can \
                                        be used to avoid merges.',
                                        epilog = 'See git pull --help for \
                                        more details')
    parser_pull.add_argument('--rebase', action = 'store_true',
                             help = 'Rebase the locally committed changes on \
                             top of the remote changes after fetching.  This \
                             can avoid a merge commit, but does rewrite local \
                             history.')
    parser_pull.add_argument('--no-rebase', action = 'store_true',
                             help = 'Do not rebase, override .git settings to \
                             automatically rebase')
    parser_pull.set_defaults(command = pull)


    # Push stuff
    parser_push = subparsers.add_parser('push',
                                        help = 'Push changes to remote '
                                        'repository')
    parser_push.set_defaults(command = push)

    # retire stuff
    parser_retire = subparsers.add_parser('retire',
                                          help = 'Retire a package',
                                          description = 'This command will \
                                          remove all files from the repo \
                                          and leave a dead.package file.')
    parser_retire.add_argument('-p', '--push',
                               default = False,
                               action = 'store_true',
                               help = 'Push changes to remote repository')
    parser_retire.add_argument('msg',
                               nargs = '?',
                               help = 'Message for retiring the package')
    parser_retire.set_defaults(command = retire)

    # sources downloads all the source files, into an optional output dir
    parser_sources = subparsers.add_parser('sources',
                                           help = 'Download source files')
    parser_sources.add_argument('--outdir',
                default = os.curdir,
                help = 'Directory to download files into (defaults to pwd)')
    parser_sources.set_defaults(command = sources)

    # srpm creates a source rpm from the module content
    parser_srpm = subparsers.add_parser('srpm',
                                        help = 'Create a source rpm')
    # optionally define old style hashsums
    parser_srpm.add_argument('--md5', action = 'store_true',
                             help = 'Use md5 checksums (for older rpm hosts)')
    parser_srpm.set_defaults(command = srpm)

    # switch branches
    parser_switchbranch = subparsers.add_parser('switch-branch',
                                                help = 'Work with branches',
                                                description = 'This command \
                                                can create or switch to a \
                                                local git branch.  It can \
                                                also be used to list the \
                                                existing local and remote \
                                                branches.')
    parser_switchbranch.add_argument('branch',  nargs = '?',
                                     help = 'Switch to or create branch')
    parser_switchbranch.add_argument('-l', '--list',
                                help = 'List both remote-tracking branches and local branches',
                                action = 'store_true')
    parser_switchbranch.set_defaults(command = switch_branch)

    # tag stuff
    parser_tag = subparsers.add_parser('tag',
                                       help = 'Management of git tags',
                                       description = 'This command uses git \
                                       to create, list, or delete tags.')
    parser_tag.add_argument('-f', '--force',
                            default = False,
                            action = 'store_true',
                            help = 'Force the creation of the tag')
    parser_tag.add_argument('-m', '--message',
                               default = None,
                               help = 'Use the given <msg> as the tag message')
    parser_tag.add_argument('-c', '--clog',
                            default = False,
                            action = 'store_true',
                            help = 'Generate the tag message from the spec changelog section')
    parser_tag.add_argument('-F', '--file',
                            default = None,
                            help = 'Take the tag message from the given file')
    parser_tag.add_argument('-l', '--list',
                            default = False,
                            action = 'store_true',
                            help = 'List all tags with a given pattern, or all if not pattern is given')
    parser_tag.add_argument('-d', '--delete',
                            default = False,
                            action = 'store_true',
                            help = 'Delete a tag')
    parser_tag.add_argument('tag',
                            nargs = '?',
                            default = None,
                            help = 'Name of the tag')
    parser_tag.set_defaults(command = tag)

    # Show unused Fedora patches; not planned
    #parser_unusedfedpatches = subparsers.add_parser('unused-fedora-patches',
    #        help = 'Print Fedora patches not used by Patch and/or ApplyPatch'
    #               ' directives')
    #parser_unusedfedpatches.set_defaults(command = unusedfedpatches)

    # Show unused patches
    parser_unusedpatches = subparsers.add_parser('unused-patches',
                                                 help = 'Print list of patches '
                                                 'not referenced by name in '
                                                 'the specfile')
    parser_unusedpatches.set_defaults(command = unusedpatches)

    # upload target takes one or more files as input
    parser_upload = subparsers.add_parser('upload',
                                          parents = [parser_newsources],
                                          conflict_handler = 'resolve',
                                          help = 'Upload source files',
                                          description = 'This command will \
                                          add a new source archive to the \
                                          lookaside cache.  The sources and \
                                          .gitignore file will be updated \
                                          with the new file(s).')
    parser_upload.set_defaults(command = new_sources, replace = False)

    # Verify %files list locally
    parser_verify_files = subparsers.add_parser('verify-files',
                                                help='Locally verify %%files '
                                                'section',
                                                description="Locally run \
                                                'rpmbuild -bl' to verify the \
                                                spec file's %files sections. \
                                                This requires a successful run \
                                                of 'fedpkg compile'")
    parser_verify_files.set_defaults(command = verify_files)

    # Get version and release
    parser_verrel = subparsers.add_parser('verrel',
                                          help = 'Print the '
                                          'name-version-release')
    parser_verrel.set_defaults(command = verrel)

    if not generate_manpage:
        # Parse the args
        return parser.parse_args()
    else:
        # Generate the man page
        import fedpkg_man_page
        fedpkg_man_page.generate(parser, subparsers)
        sys.exit(0)
        # no return possible


# The main code goes here
if __name__ == '__main__':
    args = parse_cmdline()

    if not args.path:
        try:
            args.path=os.getcwd()
        except:
            print('Could not get current path, have you deleted it?')
            sys.exit(1)

    # Import non-standard python stuff here
    import pyfedpkg

    # setup the logger -- This logger will take things of INFO or DEBUG and
    # log it to stdout.  Anything above that (WARN, ERROR, CRITICAL) will go
    # to stderr.  Normal operation will show anything INFO and above.
    # Quiet hides INFO, while Verbose exposes DEBUG.  In all cases WARN or
    # higher are exposed (via stderr).
    log = pyfedpkg.log

    if args.v:
        log.setLevel(logging.DEBUG)
    elif args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    # have to create a filter for the stdout stream to filter out WARN+
    myfilt = StdoutFilter()
    stdouthandler = logging.StreamHandler(sys.stdout)
    stdouthandler.addFilter(myfilt)
    stdouthandler.setFormatter(formatter)
    stderrhandler = logging.StreamHandler()
    stderrhandler.setLevel(logging.WARNING)
    stderrhandler.setFormatter(formatter)
    log.addHandler(stdouthandler)
    log.addHandler(stderrhandler)

    # Run the necessary command
    try:
        args.command(args)
    except KeyboardInterrupt:
        pass

# fedpkg - a Python library for Fedora Packagers
#
# Copyright (C) 2009 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

import os
import sys
import shutil
import re
import pycurl
import subprocess
import hashlib
import rpm
import logging
import git
import ConfigParser
import stat
import StringIO
import OpenSSL
import fnmatch
import offtrac


# Define some global variables, put them here to make it easy to change
LOOKASIDE = 'http://distfiles.pld-linux.org'
LOOKASIDEHASH = 'md5'
LOOKASIDE_CGI = 'https://pkgs.fedoraproject.org/repo/pkgs/upload.cgi'
LOOKASIDE_UPLOAD = 'ftp://dropin.pld-linux.org/'
GITBASEURL = 'git@github.com:pld-linux/%(module)s.git'
ANONGITURL = 'http://github.com/pld-linux/%(module)s.git'
TRACBASEURL = 'https://%(user)s:%(password)s@fedorahosted.org/rel-eng/login/xmlrpc'
UPLOADEXTS = ['tar', 'gz', 'bz2', 'lzma', 'xz', 'Z', 'zip', 'tff', 'bin',
              'tbz', 'tbz2', 'tgz', 'tlz', 'txz', 'pdf', 'rpm', 'jar', 'war',
              'db', 'cpio', 'jisp', 'egg', 'gem']
BRANCHFILTER = 'f\d\d\/master|master|el\d\/master|olpc\d\/master'

# Define our own error class
class FedpkgError(Exception):
    pass

# Setup our logger
# Null logger to avoid spurrious messages, add a handler in app code
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
# This is our log object, clients of this library can use this object to
# define their own logging needs
log = logging.getLogger("fedpkg")
# Add the null handler
log.addHandler(h)

def _find_branch(path=None, repo=None):
    """Returns the active branch name"""

    if not path:
        path = os.getcwd()

    # Create the repo from path if no repo passed
    if not repo:
        try:
            repo = git.Repo(path)
        except git.errors.InvalidGitRepositoryError:
            raise FedpkgError('%s is not a valid repo (no git checkout)' % path)
    return(repo.active_branch.name)

# Define some helper functions, they start with _
def _hash_file(file, hashtype):
    """Return the hash of a file given a hash type"""

    try:
        sum = hashlib.new(hashtype)
    except ValueError:
        raise FedpkgError('Invalid hash type: %s' % hashtype)

    input = open(file, 'rb')
    # Loop through the file reading chunks at a time as to not
    # put the entire file in memory.  That would suck for DVDs
    while True:
        chunk = input.read(8192) # magic number!  Taking suggestions
        if not chunk:
            break # we're done with the file
        sum.update(chunk)
    input.close()
    return sum.hexdigest()

def _name_from_spec(spec):
    """Return the base package name from the spec."""

    # get the name
    cmd = ['rpm', '-q', '--qf', '%{NAME} ', '--specfile', spec]
            # Run the command
    log.debug('Running: %s' % ' '.join(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    if error:
        raise FedpkgError(error)
    return output.split()[0]

def _run_command(cmd, shell=False, env=None, pipe=[], cwd=None):
    """Run the given command.

    Will determine if caller is on a real tty and if so stream to the tty

    Or else will run and log output.

    cmd is a list of the command and arguments

    shell is whether to run in a shell or not, defaults to False

    env is a dict of environment variables to use (if any)

    pipe is a command to pipe the output of cmd into

    cwd is the optional directory to run the command from

    Raises on error, or returns nothing.

    """

    # Process any environment variables.
    environ = os.environ
    if env:
        for item in env.keys():
            log.debug('Adding %s:%s to the environment' % (item, env[item]))
            environ[item] = env[item]
    # Check if we're supposed to be on a shell.  If so, the command must
    # be a string, and not a list.
    command = cmd
    pipecmd = pipe
    if shell:
        command = ' '.join(cmd)
        pipecmd = ' '.join(pipe)
    # Check to see if we're on a real tty, if so, stream it baby!
    if sys.stdout.isatty():
        if pipe:
            log.debug('Running %s | %s directly on the tty' %
                      (' '.join(cmd), ' '.join(pipe)))
        else:
            log.debug('Running %s directly on the tty' %
                      ' '.join(cmd))
        try:
            if pipe:
                # We're piping the stderr over too, which is probably a
                # bad thing, but rpmbuild likes to put useful data on
                # stderr, so....
                proc = subprocess.Popen(command, env=environ,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, shell=shell,
                                        cwd=cwd)
                subprocess.check_call(pipecmd, env=environ,
                                      stdout=sys.stdout,
                                      stderr=sys.stderr,
                                      stdin=proc.stdout,
                                      shell=shell,
                                      cwd=cwd)
                (output, err) = proc.communicate()
                if proc.returncode:
                    raise FedpkgError('Non zero exit')
            else:
                subprocess.check_call(command, env=environ, stdout=sys.stdout,
                                      stderr=sys.stderr, shell=shell,
                                      cwd=cwd)
        except (subprocess.CalledProcessError,
                OSError), e:
            raise FedpkgError(e)
        except KeyboardInterrupt:
            raise FedpkgError()
    else:
        # Ok, we're not on a live tty, so pipe and log.
        if pipe:
            log.debug('Running %s | %s and logging output' %
                      (' '.join(cmd), ' '.join(pipe)))
        else:
            log.debug('Running %s and logging output' %
                      ' '.join(cmd))
        try:
            if pipe:
                proc1 = subprocess.Popen(command, env=environ,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         shell=shell,
                                         cwd=cwd)
                proc = subprocess.Popen(pipecmd, env=environ,
                                         stdin=proc1.stdout,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, shell=shell,
                                         cwd=cwd)
                output, error = proc.communicate()
            else:
                proc = subprocess.Popen(command, env=environ,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, shell=shell,
                                        cwd=cwd)
                output, error = proc.communicate()
        except OSError, e:
            raise FedpkgError(e)
        log.info(output)
        if proc.returncode:
            raise FedpkgError('Command %s returned code %s with error: %s' %
                              (' '.join(cmd),
                               proc.returncode,
                               error))
    return

def _verify_file(file, hash, hashtype):
    """Given a file, a hash of that file, and a hashtype, verify.

    Returns True if the file verifies, False otherwise

    """

    # get the hash
    sum = _hash_file(file, hashtype)
    # now do the comparison
    if sum == hash:
        return True
    return False

def _newer(file1, file2):
    """Compare the last modification time of the given files

    Returns True is file1 is newer than file2

    """

    return os.path.getmtime(file1) > os.path.getmtime(file2)

def get_rpm_header(f, ts=None):
    """Return the rpm header."""
    if ts is None:
        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS)
    if isinstance(f, (str, unicode)):
        fo = file(f, "r")
    else:
        fo = f
    hdr = ts.hdrFromFdno(fo.fileno())
    if fo is not f:
        fo.close()
    return hdr

def _get_build_arches_from_srpm(srpm, arches):
    """Given the path to an srpm, determine the possible build arches

    Use supplied arches as a filter, only return compatible arches

    """

    archlist = arches
    hdr = get_rpm_header(srpm)
    if hdr[rpm.RPMTAG_SOURCERPM]:
        raise FedpkgError('%s is not a source package.' % srpm)
    buildarchs = hdr[rpm.RPMTAG_BUILDARCHS]
    exclusivearch = hdr[rpm.RPMTAG_EXCLUSIVEARCH]
    excludearch = hdr[rpm.RPMTAG_EXCLUDEARCH]
    # Reduce by buildarchs
    if buildarchs:
        archlist = [a for a in archlist if a in buildarchs]
    # Reduce by exclusive arches
    if exclusivearch:
        archlist = [a for a in archlist if a in exclusivearch]
    # Reduce by exclude arch
    if excludearch:
        archlist = [a for a in archlist if a not in excludearch]
    # do the noarch thing
    if 'noarch' not in excludearch and ('noarch' in buildarchs or \
                                        'noarch' in exclusivearch):
        archlist.append('noarch')
    # See if we have anything compatible.  Should we raise here?
    if not archlist:
        raise FedpkgError('No compatible build arches found in %s' % srpm)
    return archlist

def _list_branches(path=None, repo=None):
    """Returns a tuple of local and remote branch names"""

    if not path:
        path = os.getcwd()
    # Create the repo from path if no repo passed
    if not repo:
        try:
            repo = git.Repo(path)
        except git.errors.InvalidGitRepositoryError:
            raise FedpkgError('%s is not a valid repo (no git checkout)' % path)
    log.debug('Listing refs')
    refs = repo.refs
    # Sort into local and remote branches
    remotes = []
    locals = []
    for ref in refs:
        if type(ref) == git.Head:
            log.debug('Found local branch %s' % ref.name)
            locals.append(ref.name)
        elif type(ref) == git.RemoteReference:
            if ref.name == 'origin/HEAD':
                log.debug('Skipping remote branch alias origin/HEAD')
                continue # Not useful in this context
            log.debug('Found remote branch %s' % ref.name)
            remotes.append(ref.name)
    return (locals, remotes)

def _srpmdetails(srpm):
    """Return a tuple of package name, package files, and upload files."""

    # get the name
    cmd = ['rpm', '-qp', '--qf', '%{NAME}', srpm]
            # Run the command
    log.debug('Running: %s' % ' '.join(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    name = output
    if error:
        raise FedpkgError('Error querying srpm: %s' % error)

    # now get the files and upload files
    files = []
    uploadfiles = []
    cmd = ['rpm', '-qpl', srpm]
    log.debug('Running: %s' % ' '.join(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    if error:
        raise FedpkgError('Error querying srpm:' % error)
    # Doing a strip and split here as splitting on \n gets me an extra entry
    contents = output.strip().split('\n')
    # Cycle through the stuff and sort correctly by its extension
    for file in contents:
        if file.rsplit('.')[-1] in UPLOADEXTS:
            uploadfiles.append(file)
        else:
            files.append(file)

    return((name, files, uploadfiles))

def add_tag(tagname, force=False, message=None, file=None):
    """Add a git tag to the repository

    Takes a tagname

    Optionally can force the tag, include a message,
    or reference a message file.

    Runs the tag command and returns nothing

    """

    cmd = ['git', 'tag']
    cmd.extend(['-a'])
    # force tag creation, if tag already exists
    if force:
        cmd.extend(['-f'])
    # Description for the tag
    if message:
        cmd.extend(['-m', message])
    elif file:
        cmd.extend(['-F', os.path.abspath(file)])
    cmd.append(tagname)
    # make it so
    _run_command(cmd)
    log.info('Tag \'%s\' was created' % tagname)

def clean(dry=False, useignore=True):
    """Clean a module checkout of untracked files.

    Can optionally perform a dry-run

    Can optionally not use the ignore rules

    Logs output and returns nothing

    """

    # setup the command, this could probably be done with some python api...
    cmd = ['git', 'clean', '-f', '-d']
    if dry:
        cmd.append('--dry-run')
    if not useignore:
        cmd.append('-x')
    # Run it!
    _run_command(cmd)
    return
 
def clone(module, user, path=None, branch=None, bare_dir=None):
    """Clone a repo, optionally check out a specific branch.

    module is the name of the module to clone

    path is the basedir to perform the clone in

    branch is the name of a branch to checkout instead of origin/master

    bare_dir is the name of a directory to make a bare clone too if this is a
    bare clone. None otherwise.

    Logs the output and returns nothing.

    """

    if not path:
        path = os.getcwd()
    # construct the git url
    if user:
        giturl = GITBASEURL % {'user': user, 'module': module}
    else:
        giturl = ANONGITURL % {'module': module}

    # do some branch name conversions
    if branch:
        remotere = 'f\d\d|el\d|olpc\d'
        if re.match(remotere, branch):
            branch = '%s/master' % branch

    # Create the command
    cmd = ['git', 'clone']
    # do the clone
    if branch and bare_dir:
        log.debug('Cloning %s bare with branch %s' % (giturl, branch))
        cmd.extend(['--branch', branch, '--bare', giturl, bare_dir])
    elif branch:
        log.debug('Cloning %s with branch %s' % (giturl, branch))
        cmd.extend(['--branch', branch, giturl])
    elif bare_dir:
        log.debug('Cloning %s bare' % giturl)
        cmd.extend(['--bare', giturl, bare_dir])
    else:
        log.debug('Cloning %s' % giturl)
        cmd.extend([giturl])
    _run_command(cmd)

    # Set push.default to "tracking"
    if not bare_dir:
        repo = git.Repo(os.path.join(path, module))
        repo.git.config('--add', 'push.default', 'tracking')
    return

def clone_with_dirs(module, user, path=None):
    """Clone a repo old style with subdirs for each branch.

    module is the name of the module to clone

    gitargs is an option list of arguments to git clone

    """

    if not path:
        path = os.getcwd()
    # Get the full path of, and git object for, our directory of branches
    top_path = os.path.join(path, module)
    top_git = git.Git(top_path)
    repo_path = os.path.join(top_path, 'fedpkg.git')

    # construct the git url
    if user:
        giturl = GITBASEURL % {'user': user, 'module': module}
    else:
        giturl = ANONGITURL % {'module': module}

    # Create our new top directory
    try:
        os.mkdir(top_path)
    except (OSError), e:
        raise FedpkgError('Could not create directory for module %s: %s' %
                (module, e))

    # Create a bare clone first. This gives us a good list of branches
    clone(module, user, top_path, bare_dir=repo_path)
    # Get the full path to, and a git object for, our new bare repo
    repo_git = git.Git(repo_path)

    # Get a branch listing
    branches = [x for x in repo_git.branch().split() if x != "*" and
            re.match(BRANCHFILTER, x)]

    for branch in branches:
        try:
            # Make a local clone for our branch
            top_git.clone("--branch", branch, repo_path,
                          branch.split('/master')[0])

            # Set the origin correctly
            branch_path = os.path.join(top_path, branch.split('/master')[0])
            branch_git = git.Git(branch_path)
            branch_git.config("--replace-all", "remote.origin.url", giturl)
            branch_git.config('--add', 'push.default', 'tracking')
        except (git.GitCommandError, OSError), e:
            raise FedpkgError('Could not locally clone %s from %s: %s' %
                    (branch, repo_path, e))

    # We don't need this now. Ignore errors since keeping it does no harm
    shutil.rmtree(repo_path, ignore_errors=True)

    # consistent with clone method since the commands should return 0 when
    # successful.
    return 0

def commit(path=None, message=None, file=None, files=[]):
    """Commit changes to a module (optionally found at path)

    Can take a message to use as the commit message

    a file to find the commit message within

    and a list of files to commit.

    Requires the caller be a real tty or a message passed.

    Logs the output and returns nothing.

    """

    # First lets see if we got a message or we're on a real tty:
    if not sys.stdin.isatty():
        if not message and not file:
            raise FedpkgError('Must have a commit message or be on a real tty.')

    # construct the git command
    # We do this via subprocess because the git module is terrible.
    cmd = ['git', 'commit']
    if message:
        cmd.extend(['-m', message])
    elif file:
        # If we get a relative file name, prepend our path to it.
        if path and not file.startswith('/'):
            cmd.extend(['-F', os.path.abspath(os.path.join(path, file))])
        else:
            cmd.extend(['-F', os.path.abspath(file)])
    if not files:
        cmd.append('-a')
    else:
        cmd.extend(files)
    # make it so
    _run_command(cmd, cwd=path)
    return

def delete_tag(tagname, path=None):
    """Delete a git tag from the repository found at optional path"""

    if not path:
        path = os.getcwd()
    cmd = ['git', 'tag', '-d', tagname]
    _run_command(cmd, cwd=path)
    log.info ('Tag %s was deleted' % tagname)

def diff(path, cached=False, files=[]):
    """Excute a git diff

    optionally diff the cached or staged changes

    Takes an optional list of files to diff relative to the module base
    directory

    Logs the output and returns nothing

    """

    # Things work better if we're in our module directory
    oldpath = os.getcwd()
    os.chdir(path)
    # build up the command
    cmd = ['git', 'diff']
    if cached:
        cmd.append('--cached')
    if files:
        cmd.extend(files)

    # Run it!
    _run_command(cmd)
    # popd
    os.chdir(oldpath)
    return

def get_latest_commit(module):
    """Discover the latest commit has for a given module and return it"""

    # This is stupid that I have to use subprocess :/
    url = ANONGITURL % {'module': module}
    # This cmd below only works to scratch build rawhide
    # We need something better for epel
    cmd = ['git', 'ls-remote', url, 'refs/heads/master']
    try :
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        output, error = proc.communicate()
    except OSError, e:
        raise FedpkgError(e)
    if error:
        raise FedpkgError('Got an error finding head for %s: %s' %
                          (module, error))
    # Return the hash sum
    return output.split()[0]

def import_srpm(srpm, path=None):
    """Import the contents of an srpm into a repo.

    srpm: File to import contents from

    path: optional path to work in, defaults to cwd.

    This function will add/remove content to match the srpm,

    upload new files to the lookaside, and stage the changes.

    Returns a list of files to upload.

    """

    if not path:
        path = os.getcwd()
    # see if the srpm even exists
    srpm = os.path.abspath(srpm)
    if not os.path.exists(srpm):
        raise FedpkgError('File not found.')
    # bail if we're dirty
    try:
        repo = git.Repo(path)
    except git.errors.InvalidGitRepositoryError:
        raise FedpkgError('%s is not a valid repo (no git checkout)' % path)
    if repo.is_dirty():
        raise FedpkgError('There are uncommitted changes in your repo')
    # Get the details of the srpm
    name, files, uploadfiles = _srpmdetails(srpm)

    # Need a way to make sure the srpm name matches the repo some how.

    # Get a list of files we're currently tracking
    ourfiles = repo.git.ls_files().split('\n')
    # Trim out sources and .gitignore
    try:
        ourfiles.remove('.gitignore')
        ourfiles.remove('sources')
    except ValueError:
        pass
    try:
        ourfiles.remove('sources')
    except ValueError:
        pass

    # Things work better if we're in our module directory
    oldpath = os.getcwd()
    os.chdir(path)

    # Look through our files and if it isn't in the new files, remove it.
    for file in ourfiles:
        if file not in files:
            log.info("Removing no longer used file: %s" % file)
            rv = repo.index.remove([file])
            os.remove(file)

    # Extract new files
    cmd = ['rpm2cpio', srpm]
    # We have to force cpio to copy out (u) because git messes with
    # timestamps
    cmd2 = ['cpio', '-iud', '--quiet']

    rpmcall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    cpiocall = subprocess.Popen(cmd2, stdin=rpmcall.stdout)
    output, err = cpiocall.communicate()
    if output:
        log.debug(output)
    if err:
        os.chdir(oldpath)
        raise FedpkgError("Got an error from rpm2cpio: %s" % err)

    # And finally add all the files we know about (and our stock files)
    for file in ('.gitignore'):
        if not os.path.exists(file):
            # Create the file
            open(file, 'w').close()
        files.append(file)
    rv = repo.index.add(files)
    # Return to the caller and let them take it from there.
    os.chdir(oldpath)
    return(uploadfiles)

def list_tag(tagname=None):
    """Create a list of all tags in the repository which match a given tagname.

    if tagname == '*' all tags will been shown.

    """

    cmd = ['git', 'tag']
    cmd.extend(['-l'])
    if tagname != '*':
        cmd.extend([tagname])
    # make it so
    _run_command(cmd)

def new(path=None):
    """Return changes in a repo since the last tag"""

    if not path:
        path = os.getcwd()
    # setup the repo object based on our path
    try:
        repo = git.Repo(path)
    except git.errors.InvalidGitRepositoryError:
        raise FedpkgError('%s is not a valid repo (no git checkout)' % path)
    # Find the latest tag
    tag = repo.git.describe('--tags', '--abbrev=0')
    # Now get the diff
    log.debug('Diffing from tag %s' % tag)
    return repo.git.diff('-M', tag)

def pull(path=None, rebase=False, norebase=False):
    """Pull changes from the main repository using optional path

    Optionally rebase current branch on top of upstream branch

    Optionally override .git setting to always rebase

    """

    if not path:
        path = os.getcwd()
    cmd = ['git', 'pull']
    if rebase:
        cmd.append('--rebase')
    if norebase:
        cmd.append('--no-rebase')
    _run_command(cmd, cwd=path)
    return
 
def push(path=None):
    """Push changes to the main repository using optional path"""

    if not path:
        path = os.getcwd()
    cmd = ['git', 'push']
    _run_command(cmd, cwd=path)
    return

def retire(path, message=None):
    """Delete all tracked files and commit a new dead.package file

    Use optional message in commit.

    Runs the commands and returns nothing

    """

    cmd = ['git', 'rm', '-rf', path]
    _run_command(cmd, cwd=path)

    if not message:
        msg = 'Package is retired'

    fd = open(os.path.join(path, 'dead.package'), 'w')
    fd.write(msg)
    fd.close()

    cmd = ['git', 'add', os.path.join(path, 'dead.package')]
    _run_command(cmd, cwd=path)

    commit(path, msg)

    return

def _spec_archives(package):
    """parse sources from .spec"""
    # currently uses builder and adopts output for fedpkg format
#     $ builder --source-distfiles-paths eventum
#     by-md5/7/e/7eb5055260fcf096bc48b0e6c4758e3b/eventum-2.3.1.tar.gz
#     by-md5/d/e/deb6eeb2552ba757d3a949ed10c4107d/updown2.gif
    proc = subprocess.Popen(['builder -sdp %s' % package], shell=True, stdout=subprocess.PIPE)
    a = []
    for l in proc.stdout.readlines():
        (md5, file) = l.rstrip().split('/')[-2:]
        a.append('%s  %s' % (md5, file))
    return a

def sources(path, outdir=None):
    """Download source files"""

    # Get the module name
    spec = None
    # Get a list of files in the path we're looking at
    files = os.listdir(path)
    # Search the files for the first one that ends with ".spec"
    for f in files:
        if f.endswith('.spec'):
            spec = f
            break
    if not spec:
        raise FedpkgError('%s is not a valid repo (no .spec found)' % path)
    module = _name_from_spec(os.path.join(path, spec))
    try:
        archives = _spec_archives(spec)
    except IOError, e:
        raise FedpkgError('%s is not a valid repo: %s' % (path, e))
    # Default to putting the files where the module is
    if not outdir:
        outdir = path
    for archive in archives:
        try:
            # This strip / split is kind a ugly, but checksums shouldn't have
            # two spaces in them.  sources file might need more structure in the
            # future
            csum, file = archive.strip().split('  ', 1)
        except ValueError:
            raise FedpkgError('Malformed sources file.')
        # See if we already have a valid copy downloaded
        outfile = os.path.join(outdir, file)
        if os.path.exists(outfile):
            if _verify_file(outfile, csum, LOOKASIDEHASH):
                continue
        log.info("Downloading %s" % (file))
        url = '%(lookaside)s/by-md5/%(csum1)s/%(csum2)s/%(csum)s/%(file)s' % {
                'lookaside': LOOKASIDE,
                'module': module,
                'file': file.replace(' ', '%20'),
                'csum': csum,
                'csum1': csum[0],
                'csum2': csum[1],
        }
        # There is some code here for using pycurl, but for now,
        # just use subprocess
        #output = open(file, 'wb')
        #curl = pycurl.Curl()
        #curl.setopt(pycurl.URL, url)
        #curl.setopt(pycurl.FOLLOWLOCATION, 1)
        #curl.setopt(pycurl.MAXREDIRS, 5)
        #curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        #curl.setopt(pycurl.TIMEOUT, 300)
        #curl.setopt(pycurl.WRITEDATA, output)
        #try:
        #    curl.perform()
        #except:
        #    print "Problems downloading %s" % url
        #    curl.close()
        #    output.close()
        #    return 1
        #curl.close()
        #output.close()
        # These options came from Makefile.common.
        # Probably need to support wget too
        command = ['curl', '-H',  'Pragma:', '-o', file,  '-R', '-S',  '--fail',
                   '--show-error', url]
        _run_command(command)
        if not _verify_file(outfile, csum, LOOKASIDEHASH):
            raise FedpkgError('%s failed checksum' % file)
    return

def switch_branch(branch, path=None):
    """Switch the working branch

    Will create a local branch if one doesn't already exist,
    based on origin/<branch>/master

    Logs output and returns nothing.
    """

    if not path:
        path = os.getcwd()

    # setup the repo object based on our path
    try:
        repo = git.Repo(path)
    except git.errors.InvalidGitRepositoryError:
        raise FedpkgError('%s is not a valid repo (no git checkout)' % path)

    # See if the repo is dirty first
    if repo.is_dirty():
        raise FedpkgError('%s has uncommitted changes.' % path)

    # Get our list of branches
    (locals, remotes) = _list_branches(repo=repo)

    if not branch in locals:
        # We need to create a branch
        log.debug('No local branch found, creating a new one')
        if not 'origin/%s/master' % branch in remotes:
            raise FedpkgError('Unknown remote branch %s' % branch)
        try:
            log.info(repo.git.checkout('-b', branch, '--track',
                                       'origin/%s/master' % branch))
        except: # this needs to be finer grained I think...
            raise FedpkgError('Could not create branch %s' % branch)
    else:
        try:
            output = repo.git.checkout(branch)
            # The above shoudl have no output, but stash it anyway
            log.info("Switched to branch '%s'" % branch)
        except: # This needs to be finer grained I think...
            raise FedpkgError('Could not check out %s' % branch)
    return


class Lookaside(object):
    """ Object for interacting with the lookaside cache. """

    def __init__(self, url=LOOKASIDE_CGI):
        self.lookaside_cgi = url
        self.cert_file = os.path.expanduser('~/.fedora.cert')
        self.ca_cert_file = os.path.expanduser('~/.fedora-server-ca.cert')

    def _create_curl(self):
        """
        Common curl setup options used for all requests to lookaside.
        """
        curl = pycurl.Curl()

        curl.setopt(pycurl.URL, self.lookaside_cgi)

        # Set the users Fedora certificate:
        if os.path.exists(self.cert_file):
            curl.setopt(pycurl.SSLCERT, self.cert_file)
        else:
            log.warn("Missing certificate: %s" % self.cert_file)

        # Set the Fedora CA certificate:
        if os.path.exists(self.ca_cert_file):
            curl.setopt(pycurl.CAINFO, self.ca_cert_file)
        else:
            log.warn("Missing certificate: %s" % self.ca_cert_file)

        return curl

    def file_exists(self, pkg_name, filename, md5sum):
        return False
        """
        Return True if the given file exists in the lookaside cache, False
        if not.

        A FedpkgError will be thrown if the request looks bad or something
        goes wrong. (i.e. the lookaside URL cannot be reached, or the package
        named does not exist)
        """

        # String buffer, used to receive output from the curl request:
        buf = StringIO.StringIO()

        # Setup the POST data for lookaside CGI request. The use of
        # 'filename' here appears to be what differentiates this
        # request from an actual file upload.
        post_data = [
                ('name', pkg_name),
                ('md5sum', md5sum),
                ('filename', filename)]

        curl = self._create_curl()
        curl.setopt(pycurl.WRITEFUNCTION, buf.write)
        curl.setopt(pycurl.HTTPPOST, post_data)

        try:
            curl.perform()
        except:
            raise FedpkgError("Lookaside failure.  Please run 'fedora-cert -v' to verify your certificate")
        curl.close()
        output = buf.getvalue().strip()

        # Lookaside CGI script returns these strings depending on whether
        # or not the file exists:
        if output == "Available":
            return True
        if output == "Missing":
            return False

        # Something unexpected happened, will trigger if the lookaside URL
        # cannot be reached, the package named does not exist, and probably
        # some other scenarios as well.
        raise FedpkgError("Error checking for %s at: %s" %
                (filename, self.lookaside_cgi))

    def upload_file(self, pkg_name, filepath, md5sum):
        """ Upload a file to the lookaside cache. """

        # Setup the POST data for lookaside CGI request. The use of
        # 'file' here appears to trigger the actual upload:
        post_data = [
                ('name', pkg_name),
                ('md5sum', md5sum),
                ('file', (pycurl.FORM_FILE, filepath))]

        curl = self._create_curl()
        curl.setopt(pycurl.HTTPPOST, post_data)

        # TODO: disabled until safe way to test is known. Watchout for the
        # file parameter:
        try:
            curl.perform()
        except:
            raise FedpkgError('Lookaside failure.  Check your cert.')
        curl.close()

class GitIgnore(object):
    """ Smaller wrapper for managing a .gitignore file and it's entries. """

    def __init__(self, path):
        """
        Create GitIgnore object for the given full path to a .gitignore file.

        File does not have to exist yet, and will be created if you write out
        any changes.
        """
        self.path = path

        # Lines of the .gitignore file, used to check if entries need to be added
        # or already exist.
        self.__lines = []
        if os.path.exists(self.path):
            gitignore_file = open(self.path, 'r')
            self.__lines = gitignore_file.readlines()
            gitignore_file.close()

        # Set to True if we end up making any modifications, used to
        # prevent unecessary writes.
        self.modified = False

    def add(self, line):
        """
        Add a line to .gitignore, but check if it's a duplicate first.
        """

        # Append a newline character if the given line didn't have one:
        if line[-1] != '\n':
            line = "%s\n" % line

        # Add this line if it doesn't already exist:
        if not line in self.__lines:
            self.__lines.append(line)
            self.modified = True

    def match(self, line):
        line = line.lstrip('/').rstrip('\n')
        for entry in self.__lines:
            entry = entry.lstrip('/').rstrip('\n')
            if fnmatch.fnmatch(line, entry):
                return True
        return False

    def write(self):
        """ Write the new .gitignore file if any modifications were made. """
        if self.modified:
            gitignore_file = open(self.path, 'w')
            for line in self.__lines:
                gitignore_file.write(line)
            gitignore_file.close()


# Create a class for package module
class PackageModule:
    def _findbranch(self):
        """Find the branch we're on"""

        try:
            localbranch = self.repo.active_branch.name
        except TypeError, e:
            raise FedpkgError('Repo in inconsistent state: %s' % e)
        try:
            merge = self.repo.git.config('--get', 'branch.%s.merge' % localbranch)
        except git.errors.GitCommandError, e:
            raise FedpkgError('Unable to find remote branch.  Use --dist')
        return(merge.split('/')[2])

    def _getlocalarch(self):
        """Get the local arch as defined by rpm"""
        
        return subprocess.Popen(['rpm --eval %{_arch}'], shell=True,
                        stdout=subprocess.PIPE).communicate()[0].strip('\n')

    def __init__(self, path=None, dist=None):
        # Initiate a PackageModule object in a given path
        # Set some global variables used throughout
        if not path:
            path = os.getcwd()
        log.debug('Creating module object from %s' % path)
        self.path = path
        self.lookaside = LOOKASIDE
        self.lookasidehash = LOOKASIDEHASH
        self.spec = self.gimmespec()
        self.module = _name_from_spec(os.path.join(self.path, self.spec))
        self.localarch = self._getlocalarch()
        # Setup the repo
        try:
            self.repo = git.Repo(path)
        except git.errors.InvalidGitRepositoryError:
            raise FedpkgError('%s is not a valid repo (no git checkout)' % path)

        self.rpmdefines = ["--define '_sourcedir %s'" % path,
                           "--define '_specdir %s'" % path,
                           "--define '_builddir %s'" % path,
                           "--define '_srcrpmdir %s'" % path,
                           "--define '_rpmdir %s'" % path,
                           ]
        try:
            self.ver = self.getver()
            self.rel = self.getrel()
        except IndexError:
            raise FedpkgError('Could not parse spec file.')
        self.nvr = '%s-%s-%s' % (self.module, self.ver, self.rel)
        # Define the hashtype to use for srpms
        # Default to md5 hash type
        self.hashtype = 'md5'

    def clog(self):
        """Write the latest spec changelog entry to a clog file"""

        # This is a little ugly.  We want to find where %changelog starts,
        # then only deal with the content up to the first empty newline.
        # Then remove any lines that start with $ or %, and then replace
        # %% with %

        cloglines = []
        spec = open(os.path.join(self.path, self.spec), 'r').readlines()
        for line in spec:
            if line.startswith('%changelog'):
                # Grab all the lines below changelog
                for line2 in spec[spec.index(line):]:
                    if line2.startswith('\n'):
                        break
                    if line2.startswith('$'):
                        continue
                    if line2.startswith('%'):
                        continue
                    if line2.startswith('*'):
                        # skip the email n/v/r line.  Redundant
                        continue
                    cloglines.append(line2.lstrip('- ').replace('%%', '%'))
        # Now open the clog file and write out the lines
        clogfile = open(os.path.join(self.path, 'clog'), 'w')
        clogfile.writelines(cloglines)
        return

    def compile(self, arch=None, short=False):
        """Run rpm -bc on a module

        optionally for a specific arch, or short-circuit it

        Logs the output and returns nothing

        """

        # Get the sources
        sources(self.path)
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        if short:
            cmd.append('--short-circuit')
        cmd.extend(['-bc', os.path.join(self.path, self.spec)])
        # Run the command
        _run_command(cmd, shell=True)
        return

    def getver(self):
        """Return the version-release of a package module."""

        cmd = ['rpm']
        cmd.extend(self.rpmdefines)
        # We make sure there is a space at the end of our query so that
        # we can split it later.  When ther eare sub packages, we get a
        # listing for each subpackage.  We only care about the first.
        cmd.extend(['-q', '--qf', '"%{VERSION} "', '--specfile',
                    os.path.join(self.path, self.spec)])
        try:
            output = subprocess.Popen(' '.join(cmd), shell=True,
                                      stdout=subprocess.PIPE).communicate()
        except subprocess.CalledProcessError, e:
            raise FedpkgError('Could not get version of %s: %s' % (self.module, e))
        # Get just the output, then split it by space, grab the first
        return output[0].split()[0]

    def getrel(self):
        """Return the version-release of a package module."""

        cmd = ['rpm']
        cmd.extend(self.rpmdefines)
        # We make sure there is a space at the end of our query so that
        # we can split it later.  When ther eare sub packages, we get a
        # listing for each subpackage.  We only care about the first.
        cmd.extend(['-q', '--qf', '"%{RELEASE} "', '--specfile',
                    os.path.join(self.path, self.spec)])
        try:
            output = subprocess.Popen(' '.join(cmd), shell=True,
                                      stdout=subprocess.PIPE).communicate()
        except subprocess.CalledProcessError, e:
            raise FedpkgError('Could not get release of %s: %s' % (self.module, e))
        # Get just the output, then split it by space, grab the first
        return output[0].split()[0]

    def gimmespec(self):
        """Return the name of a specfile within a package module"""
    
        deadpackage = False

        # Get a list of files in the path we're looking at
        files = os.listdir(self.path)
        # Search the files for the first one that ends with ".spec"
        for f in files:
            if f.endswith('.spec'):
                return f
            if f == 'dead.package':
                deadpackage = True
        if deadpackage:
            raise FedpkgError('No spec file found. This package is retired')
        else:
            raise FedpkgError('No spec file found. Please import a new package')

    def giturl(self):
        """Return the git url that would be used for building"""

        # Get the commit hash
        commit = self.repo.iter_commits().next().sha
        url = ANONGITURL % {'module': self.module} + '?#%s' % commit
        return url

    def install(self, arch=None, short=False):
        """Run rpm -bi on a module

        optionally for a specific arch, or short-circuit it

        Logs the output and returns nothing

        """

        # Get the sources
        sources(self.path)
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        if short:
            cmd.append('--short-circuit')
        cmd.extend(['-bi', os.path.join(self.path, self.spec)])
        # Run the command
        _run_command(cmd, shell=True)
        return

    def lint(self, info=False):
        """Run rpmlint over a built srpm

        Log the output and returns nothing

        """

        # Make sure we have rpms to run on
        srpm = "%s-%s-%s.src.rpm" % (self.module, self.ver, self.rel)
        if not os.path.exists(os.path.join(self.path, srpm)):
            raise FedpkgError('Need to build srpm and rpm first')
        # Get the possible built arches
        arches = _get_build_arches_from_srpm(os.path.join(self.path, srpm),
                                             [self.localarch])
        rpms = []
        rpms.extend([os.path.join(self.path, file) for file in
                     os.listdir(self.path)
                     if file.endswith('.rpm')])
        cmd = ['rpmlint']
        if info:
            cmd.extend(['-i'])
        cmd.extend([os.path.join(self.path, srpm)])
        cmd.extend(rpms)
        # Run the command
        _run_command(cmd, shell=True)
        return

    def local(self, arch=None, hashtype='sha256'):
        """rpmbuild locally for given arch.

        Takes arch to build for, and hashtype to build with.

        Writes output to a log file and logs it to the logger

        Returns the returncode from the build call

        """

        # This could really use a list of arches to build for and loop over
        # Get the sources
        sources(self.path)
        # Determine arch to build for
        if not arch:
            arch = self.localarch
        # build up the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        # This may need to get updated if we ever change our checksum default
        if not hashtype == 'sha256':
            cmd.extend(["--define '_source_filedigest_algorithm %s'" % hashtype,
                        "--define '_binary_filedigest_algorithm %s'" % hashtype])
        cmd.extend(['--target', arch, '-ba',
                    os.path.join(self.path, self.spec)])
        logfile = '.build-%s-%s.log' % (self.ver, self.rel)
        # Run the command
        _run_command(cmd, shell=True, pipe=['tee', logfile])
        return

    def upload(self, files, replace=False, user=None, passwd=None):
        """Upload source file(s) in the lookaside cache

        Can optionally replace the existing tracked sources

        """

        oldpath = os.getcwd()
        os.chdir(self.path)

        # Will add new sources to .gitignore if they are not already there.
        gitignore = GitIgnore(os.path.join(self.path, '.gitignore'))

        lookaside = Lookaside()
        uploaded = []
        for f in files:
            # TODO: Skip empty file needed?
            file_hash = _hash_file(f, self.lookasidehash)
            log.info("Uploading: %s  %s" % (file_hash, f))
            file_basename = os.path.basename(f)

            # Add this file to .gitignore if it's not already there:
            if not gitignore.match(file_basename):
                gitignore.add('/%s' % file_basename)

            if lookaside.file_exists(self.module, file_basename, file_hash):
                # Already uploaded, skip it:
                log.info("File already uploaded: %s" % file_basename)
            else:
                # Ensure the new file is readable:
                os.chmod(f, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                #lookaside.upload_file(self.module, f, file_hash)
                # For now don't use the pycurl upload function as it does
                # not produce any progress output.  Cheat and use curl
                # directly.
                # This command is stolen from the dist-cvs make file
                # It assumes and hard codes the cert file name/location
                cmd = ['curl',
                       '--fail', '-o',
                       '/dev/null', '--show-error', '--progress-bar',
                       '--user', '%s:%s' % (user, passwd),
                       '-T', f, LOOKASIDE_UPLOAD]
                _run_command(cmd)
                uploaded.append(file_basename)

        # Write .gitignore with the new sources if anything changed:
        gitignore.write()

        rv = self.repo.index.add(['.gitignore'])

        # Change back to original working dir:
        os.chdir(oldpath)

        # Log some info
        log.info('Uploaded and added to .gitignore: %s' % ' '.join(uploaded))
        return

    def prep(self, arch=None):
        """Run rpm -bp on a module

        optionally for a specific arch

        Logs the output and returns nothing

        """

        # Get the sources
        sources(self.path)
        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if arch:
            cmd.extend(['--target', arch])
        cmd.extend(['--nodeps', '-bp', os.path.join(self.path, self.spec)])
        # Run the command
        _run_command(cmd, shell=True)
        return
 
    def srpm(self, hashtype=None):
        """Create an srpm using hashtype from content in the module
    
        Requires sources already downloaded.
    
        """

        self.srpmname = os.path.join(self.path,
                            "%s-%s-%s.src.rpm" % (self.module,
                                                  self.ver, self.rel))
        # See if we need to build the srpm
        if not os.path.exists(self.srpmname):
            log.debug('No srpm found, building one.')
        elif _newer(self.srpmname, self.spec):
            log.debug('srpm is up-to-date, skip rebuilding')
            # srpm is newer, don't redo it
            return

        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        # Figure out which hashtype to use, if not provided one
        if not hashtype:
            hashtype = self.hashtype
        # This may need to get updated if we ever change our checksum default
        if not hashtype == 'sha256':
            cmd.extend(["--define '_source_filedigest_algorithm %s'" % hashtype,
                    "--define '_binary_filedigest_algorithm %s'" % hashtype])
        cmd.extend(['--nodeps', '-bs', os.path.join(self.path, self.spec)])
        _run_command(cmd, shell=True)
        return

    def unused_patches(self):
        """Discover patches checked into source control that are not used

        Returns a list of unused patches, which may be empty.

        """

        # Create a list for unused patches
        unused = []
        # Get the content of spec into memory for fast searching
        spec = open(self.spec, 'r').read()
        # Get a list of files tracked in source control
        files = self.repo.git.ls_files('--exclude-standard').split()
        for file in files:
            # throw out non patches
            if not file.endswith('.patch'):
                continue
            if file not in spec and file.replace(self.module, '%{name}') not in spec:
                unused.append(file)
        return unused

    def verify_files(self):
        """Run rpmbuild -bl on a module to verify the %files section"""

        # setup the rpm command
        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        cmd.extend(['-bl', os.path.join(self.path, self.spec)])
        # Run the command
        _run_command(cmd, shell=True)
        return

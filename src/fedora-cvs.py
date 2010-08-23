#!/usr/bin/python

import commands
import optparse
import os
import sys
import fedora_cert
from subprocess import *

PKG_ROOT = 'cvs.fedoraproject.org:/cvs/pkgs'


def main(user, pkg_list):
    if user is not None:
        cvs_env = "CVS_RSH=ssh"
        cvs_root = ":ext:%s@%s" % (user, PKG_ROOT)
    else:
        cvs_env = ""
        cvs_root = ":pserver:anonymous@" + PKG_ROOT

    for module in pkg_list:
        print "Checking out %s from fedora CVS as %s:" % \
            (module, user or "anonymous")
        try:
            retcode = call("%s /usr/bin/cvs -d %s co %s" % (cvs_env, cvs_root, module), shell=True)
            if retcode < 0:
                print >>sys.stderr, "CVS Checkout failed Error:", -retcode
        except OSError, e:
            print >>sys.stderr, "Execution failed:", e



if __name__ == '__main__':
    opt_p = optparse.OptionParser(usage="%prog [OPTIONS] module ...")

    opts, pkgs = opt_p.parse_args()

    if len(pkgs) < 1:
        opt_p.error("You must specify at least one module to check out.")

    # Determine user name, if any
    user = None

    main(user, pkgs)

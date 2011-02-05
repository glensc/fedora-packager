# Print a man page from the help texts.


import argparse
import sys
import datetime


# We could substitute the "" in .TH with the fedpkg version if we knew it
man_header = """\
.\" man page for fedpkg
.TH fedpkg 1 "%(today)s" "" "fedora\-packager"
.SH "NAME"
fedpkg \- Fedora Packaging utility
.SH "SYNOPSIS"
.B "fedpkg"
[
.I global_options
]
.I "command"
[
.I command_options
]
[
.I command_arguments
]
.br
.B "fedpkg"
.B "help"
.br
.B "fedpkg"
.I "command"
.B "\-\-help"
.SH "DESCRIPTION"
.B "fedpkg"
is a script to interact with the Fedora Packaging system.
"""

man_footer = """\
.SH "SEE ALSO"
.UR "https://fedorahosted.org/fedora\-packager/"
.BR "https://fedorahosted.org/fedora\-packager/"
"""

class ManFormatter(object):

    def __init__(self, man):
        self.man = man

    def write(self, data):
        #print "MF:", repr(data)
        for line in data.split('\n'):
            #print 'MFL:', line
            self.man.write('  %s\n' % line)


def strip_usage(s):
    """Strip "usage: " string from beginning of string if present"""
    if s.startswith('usage: '):
        return s.replace('usage: ', '', 1)
    else:
        return s


def man_constants():
    """Global constants for man file templates"""
    today = datetime.date.today()
    today_manstr = today.strftime('%Y\-%m\-%d')
    return {'today': today_manstr}


def generate(parser, subparsers):
    """\
    Generate the man page on stdout

    Given the argparse based parser and subparsers arguments, generate
    the corresponding man page and write it to stdout.
    """

    # Not nice, but works: Redirect any print statement output to
    # stderr to avoid clobbering the man page output on stdout.
    man_file = sys.stdout
    sys.stdout = sys.stderr

    mf = ManFormatter(man_file)

    choices = subparsers.choices
    k = choices.keys()
    k.sort()

    man_file.write(man_header % man_constants())

    helptext = parser.format_help()
    helptext = strip_usage(helptext)
    helptextsplit = helptext.split('\n')
    helptextsplit = [ line for line in helptextsplit
                      if not line.startswith('  -h, --help') ]

    man_file.write('.SS "%s"\n' % ("Global Options",))

    outflag = False
    for line in helptextsplit:
        if line == "optional arguments:":
            outflag = True
        elif line == "":
            outflag = False
        elif outflag:
            man_file.write("%s\n" % line)

    help_texts = {}
    for pa in subparsers._choices_actions:
        help_texts[pa.dest] = getattr(pa, 'help', None)

    man_file.write('.SH "COMMAND OVERVIEW"\n')

    for command in k:
        cmdparser = choices[command]
        if not cmdparser.add_help:
            continue
        usage = cmdparser.format_usage()
        usage = strip_usage(usage)
        usage = ''.join(usage.split('\n'))
        usage = ' '.join(usage.split())
        if help_texts[command]:
            man_file.write('.TP\n.B "%s"\n%s\n' % (usage, help_texts[command]))
        else:
            man_file.write('.TP\n.B "%s"\n' % (usage))

    man_file.write('.SH "COMMAND REFERENCE"\n')
    for command in k:
        cmdparser = choices[command]
        if not cmdparser.add_help:
            continue

        man_file.write('.SS "%s"\n' % cmdparser.prog)

        help = help_texts[command]
        if help and not cmdparser.description:
            if not help.endswith('.'): help = "%s." % help
            cmdparser.description = help

        formatter = cmdparser.formatter_class(cmdparser.prog)
        h = cmdparser.format_help()
        mf.write(h)

    man_file.write(man_footer)

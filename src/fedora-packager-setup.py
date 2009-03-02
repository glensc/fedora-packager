#!/usr/bin/python
# -*- coding: utf-8 -*-
#  Copyright (C) 2009 Stewart Adam
#  Copyright (C) 2007, 2008, 2009 Dennis Gilmore
#  This file is part of fedora-packager.

#  fedora-packager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

#  fedora-packager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with fedora-packager.  If not, see <http://www.gnu.org/licenses/>.

import os
import string
import sys
import subprocess
import pycurl


def write_arch_config(arch, file):
    config_file = open(file, "w")
    config_file.write("""[koji]

;configuration for koji cli tool

;url of XMLRPC server
server = http://%s.koji.fedoraproject.org/kojihub

;url of web interface
weburl = http://%s.koji.fedoraproject.org/koji

;url of package download site
pkgurl = http://%s.koji.fedoraproject.org/packages

;path to the koji top directory
;topdir = /mnt/koji

;configuration for SSL athentication

;client certificate
cert = ~/.fedora.cert

;certificate of the CA that issued the client certificate
ca = ~/.fedora-upload-ca.cert

;certificate of the CA that issued the HTTP server certificate
serverca = ~/.fedora-server-ca.cert

""" % (arch, arch, arch))
    config_file.close()
    print "Wrote %s koji config file" % arch

def generate_browser_cert():
    '''Convert the user cert to the format for importing into a browser'''
    os.system('/usr/bin/openssl pkcs12 -export -in ~/.fedora.cert -CAfile ~/.fedora-upload-ca.cert -out ~/fedora-browser-cert.p12')

    print """

Browser certificate exported to ~/fedora-browser-cert.p12
To import the certificate into Firefox:

Edit -> Preferences -> Advanced
Click "View Certificates"
On "Your Certificates" tab, click "Import"
Select ~/fedora-browser-cert.p12
Type the export passphrase you chose earlier

Once imported, you should see a certificate named "Fedora Project".
Your username should appear underneath this.
 
You should now be able to click the "login" link at http://koji.fedoraproject.org/koji/ successfully.
    """
    

def download_cert(location, file):
    '''Download the cert and write to file'''
    fp = open(file, 'w')
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, location)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.WRITEDATA, fp)
    try:
        curl.perform()
    except:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
    curl.close()
    fp.close()
    print "Saved: %s" % file

def main():
    user_home = os.path.expanduser('~')
    print 'Setting up Fedora packager environment'
    user_cert = "%s/.fedora.cert" % user_home
    upload_ca_cert = '%s/.fedora-upload-ca.cert' % user_home
    server_ca_cert = '%s/.fedora-server-ca.cert' % user_home
    if not os.path.isfile(user_cert):
        print "You need a client certificate from the Fedora Account System"
        print "Please download one from https://admin.fedoraproject.org/accounts/user/gencert"
        print "Save it to ~/.fedora.cert and re-run this script"
        sys.exit(1)
    download_cert('https://admin.fedoraproject.org/accounts/fedora-server-ca.cert', server_ca_cert)
    if not os.path.islink(upload_ca_cert):
        print 'Linking: ~/.fedora-server-ca.cert to ~/.fedora-upload-ca.cert'
        os.unlink(upload_ca_cert)
        os.symlink(server_ca_cert, upload_ca_cert)
    if not os.path.isdir(os.path.join(user_home, '.koji')):
        os.mkdir(os.path.join(user_home, '.koji'))
    for arch in ['sparc', 'arm', 'alpha', 'ia64', 's390']:
        config_file = '%s/.koji/%s-config' % (user_home, arch)
        if not  os.path.isfile(config_file):
            write_arch_config(arch, config_file)
        else:
            print "koji config for %s exists" % arch
    print 'Setting up Browser Certificates'
    generate_browser_cert()

if __name__ == "__main__":
    main()
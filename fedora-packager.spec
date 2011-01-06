%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

Name:           fedora-packager
Version:        0.5.2.0
Release:        1%{?dist}
Summary:        Tools for setting up a fedora maintainer environment

Group:          Applications/Productivity
License:        GPLv2+
URL:            https://fedorahosted.org/fedora-packager
Source0:        https://fedorahosted.org/releases/f/e/fedora-packager/fedora-packager-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  python-devel
Requires:       koji bodhi-client 
Requires:       rpm-build rpmdevtools rpmlint
Requires:       mock curl openssh-clients
Requires:       pyOpenSSL python-pycurl
Requires:       redhat-rpm-config
Requires:       python-offtrac
Requires:       fedpkg = %{version}-%{release}

BuildArch:      noarch

%description
Set of utilities useful for a fedora packager in setting up their environment.

%package     -n fedpkg
Summary:        fedora utility for working with dist-git
Group:          Applications/Databases
Requires:       GitPython >= 0.2.0, python-argparse, curl
Requires:       fedora-packager = %{version}-%{release}
%if 0%{?rhel} == 5 || 0%{?rhel} == 4
Requires:       python-kitchen
%endif

%description -n fedpkg
Provides the fedpkg command for working with dist-git


%prep
%setup -q


%build
%configure
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc COPYING TODO AUTHORS ChangeLog
%{_bindir}/*
%exclude %{_bindir}/fedpkg
%{python_sitelib}/fedora_cert

%files -n fedpkg
%doc COPYING TODO AUTHORS ChangeLog
%defattr(-,root,root,-)
%{_bindir}/fedpkg
%{python_sitelib}/pyfedpkg
%{_sysconfdir}/bash_completion.d


%changelog
* Wed Jan 05 2010 Dennis Gilmore <dennis@ausil.us> - 0.5.2.0-1
- new release see ChangeLog

* Tue Aug 24 2010 Jesse Keating <jkeating@redhat.com> - 0.5.1.4-1
- Fix setting push.default when cloning with dirs
- Remove build --test option in bash completion

* Mon Aug 23 2010 Jesse Keating <jkeating@redhat.com> - 0.5.1.3-1
- Error check the update call.  #625679
- Use the correct remote when listing revs
- Add the bash completion file
- make fedora-cvs only do anonymous chackouts since cvs is read only now.
- re-fix dist defines.
- Short cut the failure on repeated builds
- Allow passing srpms to the build command
- clone: set repo's push.default to tracking
- pull the username from fedora_cert to pass to bodhi
- Catch double ^c's from build.  RHBZ #620465
- Fix up chain building
- Add missing process call for non-pipe no tty.

* Thu Aug 12 2010 Dennis Gilmore <dennis@asuil.us> - 0.5.1.2-1
- fix rh bz 619733 619879 619935 620254 620465 620595 620648
- 620653 620750 621148 621808 622291 622716

* Fri Jul 30 2010 Dennis Gilmore <dennis@ausil.us> -0.5.1.0-2
- split fedpkg out on its own

* Thu Jul 29 2010 Dennis Gilmore <dennis@ausil.us> - 0.5.1.0-1
- wrap fedora-cert in try except 
- fedpkg fixes
- require python-kitchen on EL-4 and 5

* Wed Jul 28 2010 Dennis Gilmore <dennis@ausil.us> - 0.5.0.1-1
- Fix checking for unpushed changes on a branch

* Wed Jul 28 2010 Dennis Gilmore <dennis@ausil.us> - 0.5.0-1
- update to 0.5.0 with the switch to dist-git

* Thu Jul 08 2010 Dennis Gilmore <dennis@ausil.us> - 0.4.2.2-1
- new release with lost of fedpkg fixes

* Mon Jun 14 2010 Dennis Gilmore <dennis@ausil.us> - 0.4.2.1-1
- set devel for F-14
- point builds to koji.stg
- correctly create a git url for koji

* Tue Mar 23 2010 Dennis Gilmore <dennis@ausil.us> - 0.4.2-1
- update to 0.4.2
- adds missing fedora_cert. in fedora-packager-setup bz#573941
- Require python-argparse for fedpkg bz#574206
- Require make and openssh-clients bz#542209
- Patch to make cvs checkouts more robust bz#569954

* Wed Mar 03 2010 Dennis Gilmore <dennis@ausil.us> - 0.4.1-1
- update to 0.4.1 
- adds a missing "import sys" from fedora-cert bz#570370
- Require GitPython for fedpkg

* Fri Feb 26 2010 Dennis Gilmore <dennis@ausil.us> - 0.4.0-1
- update to 0.4.0 adds fedpkg 
- make a fedora_cert python library 
- add basic date check for certs 

* Tue Aug 04 2009 Jesse Keating <jkeating@redhat.com> - 0.3.8-1
- Add fedora-hosted and require offtrac

* Thu Jul 30 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.7-1
- define user_cert in fedora-cvs before refrencing it 

* Tue Jul 28 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.6-1
- use anon checkout when a fedora cert doesnt exist bz#514108
- quote arguments passed onto rpmbuild bz#513269

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Jul 13 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.5-1
- add new rpmbuild-md5 script to build old style hash srpms
- it is a wrapper around rpmbuild

* Mon Jul  6 2009 Tom "spot" Callaway <tcallawa@redhat.com> - 0.3.4-3
- add Requires: redhat-rpm-config to be sure fedora packagers are using all available macros

* Wed Jun 24 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.4-2
- minor bump

* Mon Jun 22 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.4-1
- update to 0.3.4 
- bugfix release with some new scripts

* Mon Mar 02 2009 Dennis Gilmore <dennis@ausil.us> - 0.3.3-1
- update to 0.3.3

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Mon Aug 18 2008 Dennis Gilmore <dennis@ausil.us> - 0.3.1-1
- update to 0.3.1 fedora-cvs allows anonymous checkout
- fix some Requires  add cvs curl and wget 

* Sun Mar 30 2008 Dennis Gilmore <dennis@ausil.us> - 0.3.0-1
- update to 0.3.0 fedora-cvs uses pyOpenSSL to work out username
- remove Requires on RCS's for fedora-hosted
- rename fedora-packager-setup.sh to fedora-packager-setup

* Fri Feb 22 2008 Dennis Gilmore <dennis@ausil.us> - 0.2.0-1
- new upstream release
- update for fas2
- fedora-cvs  can now check out multiple modules at once
- only require git-core

* Mon Dec 03 2007 Dennis Gilmore <dennis@ausil.us> - 0.1.1-1
- fix typo in description 
- update to 0.1.1  fixes typo in fedora-cvs

* Sun Nov 11 2007 Dennis Gilmore <dennis@ausil.us> - 0.1-1
- initial build

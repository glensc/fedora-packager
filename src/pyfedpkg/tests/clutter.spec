Name:           clutter
Version:        0.8.6
Release:        4%{?dist}
Summary:        Open Source software library for creating rich graphical user interfaces

Group:          Development/Libraries
License:        LGPLv2+
URL:            http://www.clutter-project.org/
Source0:        http://www.clutter-project.org/sources/%{name}/0.8/%{name}-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  glib2-devel mesa-libGL-devel gtk2-devel pkgconfig pango-devel
BuildRequires:  libXdamage-devel gettext gtk-doc

%description
Clutter is an open source software library for creating fast, 
visually rich graphical user interfaces. The most obvious example 
of potential usage is in media center type applications. 
We hope however it can be used for a lot more.

%package devel
Summary:        Clutter development environment
Group:          Development/Libraries
Requires:      %{name} = %{version}-%{release}
Requires:       pkgconfig glib2-devel pango-devel fontconfig-devel gtk2-devel
Requires:       mesa-libGL-devel

%description devel
Header files and libraries for building a extension library for the
clutter


%package        doc
Summary:        Documentation for %{name}
Group:          Documentation
Requires:       %{name} = %{version}-%{release}

%description    doc
Clutter is an open source software library for creating fast, 
visually rich graphical user interfaces. The most obvious example 
of potential usage is in media center type applications. 
We hope however it can be used for a lot more.

This package contains documentation for clutter.


%prep
%setup -q

%build
%configure --with-bar \
	   --disable-gtk-doc \
           --with-foo
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
#make DESTDIR=$RPM_BUILD_ROOT install
make DESTDIR=$RPM_BUILD_ROOT install INSTALL="%{__install} -p -c"

%clean
rm -rf $RPM_BUILD_ROOT

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING NEWS README
%exclude %{_libdir}/*.la
%{_libdir}/*.so.0
%{_libdir}/*.so.0.*

%files devel
%defattr(-, root, root)
%{_includedir}/*
%{_libdir}/*.so
%{_libdir}/pkgconfig/*.pc

%files doc
%defattr(-, root, root)
#%dir %{_datadir}/gtk-doc/html/clutter
%{_datadir}/gtk-doc/html/clutter
#%dir %{_datadir}/gtk-doc/html/cogl
%{_datadir}/gtk-doc/html/cogl


%changelog
* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.6-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild


* Wed Jan 21 2009 Allisson Azevedo <allisson@gmail.com> 0.8.6-3
- Remove noarch from doc subpackage

* Wed Jan 21 2009 Allisson Azevedo <allisson@gmail.com> 0.8.6-2
- Added gtk-doc for cogl
- Created doc subpackage

* Wed Jan 21 2009 Allisson Azevedo <allisson@gmail.com> 0.8.6-1
- Update to 0.8.6

* Mon Oct  6 2008 Allisson Azevedo <allisson@gmail.com> 0.8.2-1
- Update to 0.8.2
- Removed clutter-0.8.0-clutter-fixed.patch

* Sat Sep  6 2008 Allisson Azevedo <allisson@gmail.com> 0.8.0-1
- Update to 0.8.0
- Added clutter-0.8.0-clutter-fixed.patch

* Sat Jun 14 2008 Allisson Azevedo <allisson@gmail.com> 0.6.4-1
- Update to 0.6.4

* Sat May 17 2008 Allisson Azevedo <allisson@gmail.com> 0.6.2-1
- Update to 0.6.2

* Tue Feb 19 2008 Allisson Azevedo <allisson@gmail.com> 0.6.0-1
- Update to 0.6.0

* Mon Feb 18 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.4.2-2
- Autorebuild for GCC 4.3

* Wed Oct  3 2007 Allisson Azevedo <allisson@gmail.com> 0.4.2-1
- Update to 0.4.2

* Mon Sep  3 2007 Allisson Azevedo <allisson@gmail.com> 0.4.1-1
- Update to 0.4.1

* Sat Jul 21 2007 Allisson Azevedo <allisson@gmail.com> 0.3.1-1
- Update to 0.3.1

* Thu Apr 12 2007 Allisson Azevedo <allisson@gmail.com> 0.2.3-1
- Update to 0.2.3

* Sun Mar 28 2007 Allisson Azevedo <allisson@gmail.com> 0.2.2-4
- Changed buildrequires and requires

* Sun Mar 27 2007 Allisson Azevedo <allisson@gmail.com> 0.2.2-3
- Fix .spec

* Sun Mar 24 2007 Allisson Azevedo <allisson@gmail.com> 0.2.2-2
- Fix .spec

* Sun Mar 23 2007 Allisson Azevedo <allisson@gmail.com> 0.2.2-1
- Initial RPM release

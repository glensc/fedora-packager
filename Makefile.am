bin_SCRIPTS = fedora-cvs \
	fedora-packager-setup \
	fedoradev-pkgowners \
	fedora-cert \
	fedora-getsvn \
	fedora-hosted \
	rpmbuild-md5 \
	fedpkg \
	sparc-koji \
	s390-koji \
	arm-koji \
	ppc-koji

sbin_SCRIPTS = fedora-burn-yubikey

CLEANFILES = $(bin_SCRIPTS) $(sbin_SCRIPTS)

EXTRA_DIST = src/fedora-cvs.py \
	src/fedora-packager-setup.py \
	src/fedoradev-pkgowners \
	src/fedora-cert.py \
	src/fedora-getsvn \
	src/fedora-hosted.py \
	src/fedora-burn-yubikey.py \
	src/rpmbuild-md5 \
	src/fedpkg.py \
	src/secondary-koji \
	src/fedpkg.bash

fedora-cvs: $(srcdir)/src/fedora-cvs.py
	rm -f fedora-cvs
	install -p -m 755 -T $(srcdir)/src/fedora-cvs.py fedora-cvs

fedora-packager-setup: $(srcdir)/src/fedora-packager-setup.py
	rm -f fedora-packager-setup
	install -p -m 755 -T $(srcdir)/src/fedora-packager-setup.py fedora-packager-setup

fedoradev-pkgowners: $(srcdir)/src/fedoradev-pkgowners
	rm -f fedoradev-pkgowners
	install -p -m 755 -T $(srcdir)/src/fedoradev-pkgowners fedoradev-pkgowners

fedora-cert: $(srcdir)/src/fedora-cert.py
	rm -f fedora-cert
	install -p -m 755 -T $(srcdir)/src/fedora-cert.py fedora-cert

fedora-getsvn: $(srcdir)/src/fedora-getsvn
	rm -f fedora-getsvn
	install -p -m 755 -T $(srcdir)/src/fedora-getsvn fedora-getsvn

fedora-hosted: $(srcdir)/src/fedora-hosted.py
	rm -f fedora-hosted
	install -p -m 755 -T $(srcdir)/src/fedora-hosted.py fedora-hosted

fedora-burn-yubikey: $(srcdir)/src/fedora-burn-yubikey.py
	rm -f fedora-burn-yubikey
	install -p -m 755 -T $(srcdir)/src/fedora-burn-yubikey.py fedora-burn-yubikey

rpmbuild-md5: $(srcdir)/src/rpmbuild-md5
	rm -f rpmbuild-md5
	install -p -m 755 -T $(srcdir)/src/rpmbuild-md5 rpmbuild-md5

fedpkg: $(srcdir)/src/fedpkg.py
	rm -f fedpkg
	install -p -m 755 -T $(srcdir)/src/fedpkg.py fedpkg

sparc-koji: $(srcdir)/src/secondary-koji
	rm -f sparc-koji
	install -p -m 755 -T $(srcdir)/src/secondary-koji sparc-koji

arm-koji: $(srcdir)/src/secondary-koji
	rm -f arm-koji
	install -p -m 755 -T $(srcdir)/src/secondary-koji arm-koji

s390-koji: $(srcdir)/src/secondary-koji
	rm -f s390-koji
	install -p -m 755 -T $(srcdir)/src/secondary-koji s390-koji

ppc-koji: $(srcdir)/src/secondary-koji
	rm -f ppc-koji
	install -p -m 755 -T $(srcdir)/src/secondary-koji ppc-koji

if HAVE_PYTHON
CLEANFILES += fedpkg.1
man1_MANS = fedpkg.1
fedpkg.1: fedpkg
	tmpfile="fedpkg.1.$$$$"; \
	if env PYTHONPATH=$(srcdir)/src python -c 'import fedpkg; fedpkg.parse_cmdline(True)' > "$$tmpfile"; then \
		mv -f "$$tmpfile" "$@"; \
	else \
		rm -f "$$tmpfile"; \
		s="$$?"; \
		echo "Error generating man page: $$s"; \
		exit "$$s"; \
	fi
endif

noinst_PYTHON = $(srcdir)/src/fedpkg_man_page.py
pyfedpkg_PYTHON = $(wildcard $(srcdir)/src/pyfedpkg/*.py)
fedora_cert_PYTHON = $(wildcard $(srcdir)/src/fedora_cert/*.py)

fedora_certdir = $(pythondir)/fedora_cert
pyfedpkgdir = $(pythondir)/pyfedpkg

bashconfdir = $(sysconfdir)/bash_completion.d
bashconf_DATA = $(srcdir)/src/fedpkg.bash

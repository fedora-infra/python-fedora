%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-fedora
Version:        0.3.9
Release:        1%{?dist}
Summary:        Python modules for talking to Fedora Infrastructure Services

Group:          Development/Languages
License:        GPLv2
URL:            https://fedorahosted.org/python-fedora/
Source0:        https://fedorahosted.org/releases/p/y/%{name}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel
BuildRequires:  python-setuptools-devel
BuildRequires:  python-paver
BuildRequires:  python-sphinx
Requires:       python-simplejson
Requires:       python-bugzilla
Requires:       python-feedparser
Requires:       python-sqlalchemy
Requires:       python-decorator
Requires:       python-pycurl
# These are now optional dependencies.  Some bodhi methods will not work if
# they aren't installed but they aren't needed for most functionality of the
# module.
#Requires:       koji python-iniparse yum
Provides:       python-fedora-infrastructure = %{version}-%{release}
Obsoletes:      python-fedora-infrastructure < %{version}-%{release}

%description
Python modules that help with building Fedora Services.  This includes a JSON
based auth provider for authenticating against FAS2 over the network and a
client that handles communication with the servers.  The client module can
be used to build programs that communicate with Fedora Infrastructure's
TurboGears Applications such as Bodhi, PackageDB, MirrorManager, and FAS2.

%prep
%setup -q

%build
paver build
paver html

%install
rm -rf $RPM_BUILD_ROOT
paver install --skip-build --root $RPM_BUILD_ROOT
mv build-doc/html doc/

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README COPYING AUTHORS ChangeLog doc
%{python_sitelib}/*

%changelog
* Sun Feb 8 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.9-1
- New upstream with important bugfixes.

* Thu Nov 20 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.8-1
- New upstream with pycurl client backend, more fas methods, and bodhi bugfix.

* Thu Oct 30 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.7-1
- New upstream has more complete pkgdb integration.

* Mon Sep 15 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.6-2
- Add python-sphinx to the buildrequires.

* Mon Sep 15 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.6-1
- New upstream.  No longer deps on koji.

* Mon Aug 25 2008 Luke Macken <lmacken@redhat.com> - 0.3.5-1
- New upstream release

* Mon Jul 28 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.4-1
- Small fix to proxyclient.send_request() for sequence types.

* Wed Jul 23 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.3-1
- A few fixes for the new fas release.

* Sun Jul 20 2008 Luke Macken <lmacken@redhat.com> - 0.3.2-1
- Latest upstream release
- Add koji to the Requires

* Mon Jul 14 2008 Luke Macken <lmacken@redhat.com> - 0.3.1-1
- New upstream bugfix release

* Wed Jul 02 2008 Luke Macken <lmacken@redhat.com> - 0.3-1
- New upstream release.

* Wed Apr 23 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.11.1-1
- Fix a crasher bug.

* Wed Apr 23 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.11-1
- New upstream release.

* Wed Apr 23 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.10-1
- New upstream release.

* Sun Apr 20 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.9-1
- New upstream release.

* Sat Apr 12 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.8-1
- New upstream release to fix two bugs found by a pylint run.

* Fri Apr 11 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.2.99.7-1
- Add a method to accounts.fas2.AccountSystem to speed up retrieval of user
  information.

* Mon Apr 7 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.2.99.6-1
- Add gencert method in fedora.accounts.fas2
- Remove old python-ldap dependency.
- Toshio Kuratomi added:
  * Merge infrastructure subpackage into main package.
  * Remove FAS1 code.
  * Fix JsonVisitManager race condition.
  * Start documentation on BaseClient/Fedora Service Architecture.

* Tue Mar 18 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.2.99.5-1
- Add fas2.py (an interface for apps to fetch data from FAS2 using
  fedora.tg.client)

* Tue Mar 11 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.4-1
- Change from Ricky to enable user.human_name.

* Tue Mar 11 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.3-1
- Fix a bug in BaseClient.

* Fri Mar 7 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.2-2
- Small updates to description of -infrastructure as we're no longer tied to
  Fedora Infrastructure boxes.

* Mon Mar 3 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.2-1
- Third beta.  Changes to accomodate FAS2 included as FAS2, TG-1.0.4, and
  SA-0.4 are going to all roll into the new platform together.

* Sun Feb 17 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.1-1
- Second beta.

* Wed Feb 13 2008 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.99.0-1
- First beta of new release.  This release is for TG-1.0.4 and SA-0.4.

* Thu Dec 13 2007 Luke Macken <lmacken@redhat.com> - 0.2.90.22-1
- Convert fasLDAP to get its connection information fedora-db-access.
- Add requirements for python-feedparser and python-bugzilla
- Add fedora.tg.widgets module containing a few proof-of-concept
  Fedora TurboGears widgets
- Add a new method to fas: get_users() that returns common public information
  about all users.

* Thu Nov 15 2007 Toshio Kuratomi <tkuratom@redhat.com> - 0.2.90.21-1
- Bugfix release for expired sessions.

* Wed Nov 14 2007 Luke Macken <lmacken@redhat.com> - 0.2.90.20-3
- Handle our SQLAlchemy requirement differently for Fedora 8+, until
  TurboGears can use SQLAlchemy >= 0.4

* Wed Nov  7 2007 Luke Macken <lmacken@redhat.com> - 0.2.90.20-2
- Require SQLAlchemy 0.3 for python-fedora-infrastructure

* Wed Nov  7 2007 Luke Macken <lmacken@redhat.com> - 0.2.90.20-1
- Latest upstream release

* Tue Sep 25 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.19-1
- New upstream release with a FAS2 unicode fix.

* Mon Sep 24 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.18-3
- Fix the Source URL.  Should be fedorapeople rather than fedoraproject.

* Fri Sep 21 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.18-2
- BR: python-setuptools-devel as this has been split in the new versions.

* Tue Sep 18 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.18-1
- Update to version wih handling of control-center-maint bugzilla address.

* Tue Sep 18 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.17-2
- Minor touchups to description and URL.

* Mon Sep 17 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.17-1
- Update to 0.2.90.17. 
- Build separate packages for pieces useful on clients and only on the server.

* Mon Sep 10 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.16-1
- Bugfix to fasLDAP module.

* Fri Sep 7 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.15-1
- Make the fasLDAP module more OO.
- Bugfixes.
- Update the install line.

* Thu Aug 2 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.14-1
- Fix safas2provider to only create the visit_identity class.
- Add COPYING and AUTHORS files.

* Sat Jul 21 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.13-1
- New class fedora.tg.client.BaseClient that can be used as the basis of a TG
  standalone application.  With a little support on the server side (mostly
  allowing tg_format=json) this class will provide you with the basis to read
  and write data to the server.
- Fix safasprovider to only create the visit_identity class since the other
  information is stored directly in FAS.

* Mon Jul 10 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.12-1
- Fix some issues with Unicode.
- Catch a traceback when the database is down.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.11-1
- Remove a decorator so running on python-2.3 works.
- Have FASUser and FASGroup emit json on demand so that they can be returned
  when tg_format=json.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.10-1
- Update fas2 integration with changes from mmcgrath.
- berrange has changed his email address in the account system, no longer need
  to special case his bugzilla address.
- Fix a bug in the handling of db errors in accounts/fas.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.9-1
- Update fas2 integration with changes from mmcgrath.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.8-1
- Catch some exceptions when the database connection dies.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.7-1
- Fix another bug with the new bugzilla email code.  Need to grab the user
  email from the database even if unathenticated so bugzilla_email has
  something to pull from.

* Sun Apr 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.6-1
- Fix bug with the new bugzilla email code.

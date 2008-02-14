%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           python-fedora
Version:        0.2.99.0
Release:        1%{?dist}
Summary:        Python modules for talking to Fedora Infrastructure Services

Group:          Development/Languages
License:        GPLv2
URL:            http://hosted.fedoraproject.org/projects/python-fedora/
Source0:        http://toshio.fedorapeople.org/fedora/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel python-setuptools-devel
Requires:       python-simplejson

%description
Python modules that handle communication with Fedora Infrastructure services.
This set of modules helps with building clients that talk to Fedora
Infrastructure's  TurboGears based services such as Bodhi, PackageDB,
MirrorManager, and FAS2.

%package infrastructure
Summary: Python modules for building Fedora Infrastructure Services
Group: Development/Languages
Requires: %{name} = %{version}-%{release}
Requires: python-psycopg2
Requires: python-bugzilla
Requires: python-feedparser
Requires: python-ldap
# This can go away when TurboGears can use SQLAlchemy >= 0.4
%if 0%{?fedora} >= 8
Requires: python-sqlalchemy0.3
%else
Requires: python-sqlalchemy
%endif

%description infrastructure
Additional python modules that can be used on Fedora Infrastructure Servers to
help build new services.  This includes the server's authentication providers.

%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT

 
%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README COPYING AUTHORS ChangeLog
%dir %{python_sitelib}/fedora
%dir %{python_sitelib}/fedora/tg
%{python_sitelib}/fedora/__init__.py*
%{python_sitelib}/fedora/tg/__init__.py*
%{python_sitelib}/fedora/tg/client.py*
%{python_sitelib}/python_fedora-%{version}-py%{pyver}.egg-info

%files infrastructure
%defattr(-,root,root,-)
%{python_sitelib}/fedora/accounts/
%{python_sitelib}/fedora/tg/identity/
%{python_sitelib}/fedora/tg/visit/
%{python_sitelib}/fedora/tg/widgets.py*

%changelog
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

* Tue Apr 3 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.5-1
- Update to latest fasLDAP.py.
- Return bugzilla email address.
- Add a method to lookup by email address.  This includes bugzilla email
  addresses given in owners.list.

* Wed Mar 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.4-1
- Fix a bug with get_group_info().
- Fix a bug in exception handling in the turbogears identity handler.

* Wed Mar 14 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.3-1
- Fix a bug in exception handling.
- Fix a bug where we were not seeing updates to the FAS.
  + In order to do this efficiently we also introduce a dependency on
    sqlalchemy (for database connection pooling).

* Fri Feb 9 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.90.2-1
- Experimental fas2 support.

* Fri Feb 9 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.1-1
- Fix a brown paper bag issue.

* Fri Feb 9 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2-1
- Bug fix for tg sessions.

* Thu Jan 18 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.1-1
- Initial RPM Package.

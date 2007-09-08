%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-fedora
Version:        0.2.90.15
Release:        1%{?dist}
Summary:        Python modules for integrating into Fedora Infrastructure

Group:          Development/Languages
License:        GPLv2
URL:            http://www.fedoraproject.org/wiki/Infrastructure/AccountSystem2/API
Source0:        http://toshio.fedoraproject.org/fedora/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel
BuildRequires:  python-setuptools
Requires: python-psycopg2
Requires: python-sqlalchemy

%description
Python modules that allow your program to integrate with Fedora Infrastructure.

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
%doc README COPYING AUTHORS
%{python_sitelib}/*


%changelog
* Fri Sep 7 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.2.90.15-1
- Make the fasLDAP module more OO.
- Bugfixes.

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

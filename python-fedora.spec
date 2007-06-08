%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-fedora
Version:        0.2.90.9
Release:        1%{?dist}
Summary:        Python modules for integrating into Fedora Infrastructure

Group:          Development/Languages
License:        GPL
URL:            http://www.fedoraproject.org/wiki/Infrastructure/AccountSystem2/API
Source0:        http://www.tiki-lounge.com/~toshio/fedora/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel
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
%{__python} setup.py install -O1 --skip-build --single-version-externally-managed --root $RPM_BUILD_ROOT

 
%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README
%{python_sitelib}/*


%changelog
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

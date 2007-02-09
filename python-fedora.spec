%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-fedora
Version:        0.2.1
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
* Fri Feb 9 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2.1-1
- Fix a brown paper bag issue.

* Fri Feb 9 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.2-1
- Bug fix for tg sessions.

* Thu Jan 18 2007 Toshio Kuratomi <toshio@tiki-lounge.com> - 0.1-1
- Initial RPM Package.

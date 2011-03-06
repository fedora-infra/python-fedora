%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%global prerel a1

Name:           python-fedora
Version:        0.3.21
Release:        0.%{prerel}%{?dist}
Summary:        Python modules for talking to Fedora Infrastructure Services

Group:          Development/Languages
License:        LGPLv2+
URL:            https://fedorahosted.org/python-fedora/
Source0:        https://fedorahosted.org/releases/p/y/%{name}/%{name}-%{version}%{?prerel}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-paver >= 1.0
BuildRequires:  python-sphinx
%if 0%{?fedora} >= 9 || 0%{?rhel} > 5
BuildRequires:  python-cherrypy2
%else
BuildRequires:  python-cherrypy
%endif
BuildRequires:  python-babel
BuildRequires:  TurboGears2
BuildRequires:  python-nose
BuildRequires:  python-kitchen
BuildRequires:  python-bunch
Requires:       python-simplejson
Requires:       python-bugzilla
Requires:       python-bunch
Requires:       python-feedparser
Requires:       python-sqlalchemy
Requires:       python-decorator
Requires:       python-pycurl
Requires:       python-kitchen
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
%setup -q -n %{name}-%{version}%{?prerel}

%build
paver build
paver html

%install
rm -rf %{buildroot}
paver install --skip-build --root %{buildroot}

mv build-doc/html doc/
%find_lang %{name}

%clean
rm -rf %{buildroot}

%files -f %{name}.lang
%defattr(-,root,root,-)
%doc NEWS README COPYING AUTHORS ChangeLog doc
%{python_sitelib}/*

%changelog
* Thu Apr 22 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.21-0.a1
- 0.3.21 alpha1 release.

* Thu Apr 22 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.20-1
- 0.3.20 release

* Wed Apr 21 2010 Luke Macken <lmacken@redhat.com> - 0.3.19-1
- 0.3.19 release

* Mon Mar 15 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.18.90-1
- 0.3.18.90: beta of a bugfix release

* Mon Mar 15 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.18-1
- 0.3.18 bugfix.

* Thu Mar 11 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.17-1
- New release 0.3.17.

* Wed Oct 21 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.16-1
- New release 0.3.16.

* Mon Aug 06 2009 Ricky Zhou <ricky@fedoraproject.org> - 0.3.15-1
- New release 0.3.15.
- Relicensed to LGPLv2+

* Mon Jul 27 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.14-1
- New release 0.3.14.

* Sat Jun 13 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.13.1-1
- Merge 0.3.12.1 and 0.3.13 releases together.

* Sat Jun 13 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.13-1
- New release.  Some new pkgdb API, defaultdict implementation, and a
  bugfix to response code from the shipped login controller.

* Wed Jun 11 2009 Ricky Zhou <ricky@fedoraproject.org> - 0.3.12.1-2
- Backport a patch to add a bugzilla_email entry.

* Wed Jun 03 2009 Ricky Zhou <ricky@fedoraproject.org> - 0.3.12.1-1
- Update for new FAS release.

* Thu Mar 19 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.12-1
- Bugfix and cleanup release.

* Thu Mar 12 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.11.1-1
- Update to fix problem with django auth and redirects.

* Mon Mar 9 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.11-1
- readd the old jsonfasproviders.

* Fri Mar 6 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10-1
- CSRF fixes and django authentication provider.

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sun Feb 8 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.9-1
- New upstream with important bugfixes.

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.3.8-2
- Rebuild for Python 2.6

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

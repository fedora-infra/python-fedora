%if 0%{?rhel} && 0%{?rhel} <= 6
%{!? __python2: %global __python2 /usr/bin/python2}
%{!? python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif
#%%global prerel c2

Name:           python-fedora
Version:        0.3.33
Release:        1%{?dist}
Summary:        Python modules for talking to Fedora Infrastructure Services

Group:          Development/Languages
License:        LGPLv2+
URL:            https://fedorahosted.org/python-fedora/
Source0:        https://fedorahosted.org/releases/p/y/%{name}/%{name}-%{version}%{?prerel}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
%if 0%{?rhel} && 0%{?rhel} <= 6
BuildRequires:  python-sphinx10
%else
BuildRequires:  python-sphinx
%endif
%if 0%{?fedora} || 0%{?rhel} > 5
BuildRequires:  python-cherrypy2
%else
BuildRequires:  python-cherrypy
%endif
BuildRequires:  python-babel
BuildRequires:  TurboGears2
BuildRequires:  python-nose
BuildRequires:  python-kitchen
BuildRequires:  python-bunch
# Needed for tests and for the way we build docs
BuildRequires: TurboGears python-repoze-who-friendlyform Django
BuildRequires: python-requests
BuildRequires: python-openid
BuildRequires: python-openid-teams
BuildRequires: python-openid-cla

Requires:       python-simplejson
Requires:       python-bunch
Requires:       python-kitchen
Requires:       python-requests
# These are now optional dependencies.  Some bodhi methods will not work if
# they aren't installed but they aren't needed for most functionality of the
# module.
#Requires:       koji python-iniparse yum

%description
Python modules that help with building Fedora Services.  The client module
included here can be used to build programs that communicate with Fedora
Infrastructure's TurboGears Applications such as Bodhi, PackageDB,
MirrorManager, and FAS2.

%package turbogears
Summary: Python modules for TurboGears applications in Fedora Infrastructure
Group:          Development/Languages
License:        LGPLv2+
Requires: %{name} = %{version}-%{release}
Requires: TurboGears
Requires: python-sqlalchemy
Requires: python-decorator
Requires: python-bugzilla
Requires: python-feedparser

%description turbogears
Python modules that help with building Fedora Services.  This package includes
a JSON based auth provider for authenticating TurboGears1 applications against
FAS2 over the network, a csrf protected version of the standard TG1 auth
provider, templates to help build CSRF-protected login forms, and miscellaneous
other helper functions for TurboGears applications.

%package turbogears2
Summary: Python modules for TurboGears applications in Fedora Infrastructure
Group:          Development/Languages
License:        LGPLv2+
Requires: %{name} = %{version}-%{release}
Requires: TurboGears2
Requires: python-sqlalchemy
%if 0%{?fedora}
Requires: python-mako >= 0.3.6
%else if 0%{?rhel} && 0%{?rhel} <= 6
Requires: python-mako0.4 >= 0.3.6
%endif
Requires: python-repoze-who-friendlyform

%description turbogears2
Python modules that help with building Fedora Services.  This package includes
middleware for protecting against CSRF attacks, repoze.who authenticators for
logging in to TurboGears2 services based on account information lp build
CSRF-protected login forms, and miscellaneous other helper functions for
TurboGears2 applications.

%package django
Summary: Python modules for django applications authing to Fedora Account System
Group:          Development/Languages
License:        LGPLv2+
Requires: %{name} = %{version}-%{release}
Requires: Django

%description django
Python modules that help with building Fedora Services.  This package includes
an auth provider to let django applications authenticate against the Fedora
Account System.

%package flask
Summary: Python modules for flask applications authing to Fedora Account System
Group:          Development/Languages
License:        LGPLv2+
Requires: %{name} = %{version}-%{release}
Requires: python-flask
Requires: python-flask-wtf
Requires: python-openid
Requires: python-openid-teams
Requires: python-openid-cla

%description flask
Python modules that help with building Fedora Services.  This package includes
an auth provider to let flask applications authenticate against the Fedora
Account System.

%prep
%setup -q -n %{name}-%{version}%{?prerel}

%build
python2 setup.py build
python2 setup.py build_sphinx
python2 releaseutils.py build_catalogs

%install
rm -rf %{buildroot}
python2 setup.py install --skip-build --root %{buildroot}
DESTDIR=%{buildroot} python2 releaseutils.py install_catalogs

# Cleanup doc
mv build/sphinx/html doc/
if test -e doc/html/.buildinfo ; then
  rm doc/html/.buildinfo
fi
find doc -name 'EMPTY' -exec rm \{\} \;

# Remove regression tests
rm -rf %{buildroot}%{python2_sitelib}/fedora/wsgi/test

%find_lang %{name}

%clean
rm -rf %{buildroot}

%files -f %{name}.lang
%defattr(-,root,root,-)
%doc NEWS README COPYING AUTHORS doc
%{python2_sitelib}/*
%exclude %{python2_sitelib}/fedora/tg/
%exclude %{python2_sitelib}/fedora/tg2/
%exclude %{python2_sitelib}/fedora/wsgi/
%exclude %{python2_sitelib}/fedora/django/
%exclude %{python2_sitelib}/flask_fas.py*
%exclude %{python2_sitelib}/flask_fas_openid.py*

%files turbogears
%{python2_sitelib}/fedora/tg/

%files turbogears2
%{python2_sitelib}/fedora/wsgi/
%{python2_sitelib}/fedora/tg2/

%files django
%{python2_sitelib}/fedora/django/

%files flask
%{python2_sitelib}/flask_fas.py*
%{python2_sitelib}/flask_fas_openid.py*

%changelog
* Thu Dec 19 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.33-1
- Update for final release with numerous flask_fas_openid fixes

* Mon Jul 29 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.32.3-3
- Update flask_fas_openid to fix imports

* Tue Jul 23 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.32.3-2
- Add the flask_fas_openid identity provider for flask

* Tue Feb  5 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.32.3-1
- Upstream update to fix BodhiClient's knowledge of koji tags (ajax)

* Mon Feb 04 2013 Toshio Kuratomi <toshio@fedoraproject.org> 0.3.32.2-1
- Upstream update fixing a bug interacting with python-requests

* Thu Jan 24 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.32.1-1
- Fix a documentation bug that slipped through

* Wed Jan 23 2013 Ralph Bean <rbean@redhat.com> - 0.3.32-1
- Replace pyCurl with python-requests in ProxyClient.

* Tue Jan 22 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.31-1
- Minor bugfix release

* Thu Jan 10 2013 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.30-1
- Make TG's loginForm and CSRF's text translated from tg-apps (laxathom).
- Fix a bug in fedora.tg.utils.tg_absolute_url
- Add a lookup email parameter to gravatar lookups
- Add an auth provider for flask

* Wed Jun 6 2012 Ricky Elrd <codeblock@fedoraproject.org> - 0.3.29-1
- Add a create_group() method to AccountSystem.

* Tue Apr 17 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.28.1-1
- Apply the apache-curl workaround unconditionally, not just when doing
  authenticated requests

* Tue Apr 17 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.28-1
- Bugfix for a bad interaction between curl and the apache version running on
  Fedora Infrastructure leading to Http 417 errors.
- Bugfix for older Django installations.

* Thu Mar 8 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.27-1
- Bugfix release for servers using tg-1.1.x

* Mon Feb 13 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.26-1
- Final release.

* Thu Dec 22 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.25.92-1
- Third beta release

* Sun Nov 20 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.25.90-1
- Beta release

* Thu Oct 6 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.25.1-1
- Minor update to bugzilla email aliases

* Sat Sep 3 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.25-1
- Upstream bugfix release that makes many TG2-server helper function more usable
- Also, split the TG2 functionality into a separate subpackage from the TG1
  functions

* Tue Aug 9 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.24-3
- Get the PYTHONPATH for building docs correct

* Tue Aug 9 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.24-2
- Rework package to provide the turbogears and django code in subpackages with
  full dependencies for each of those.

* Wed Jul 20 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.24-1
- Upstream 0.3.24 release bugfixing TG2 server utils and clients with
  session cookie auth.

* Tue May 03 2011 Luke Macken <lmacken@redhat.com> - 0.3.23-1
- Upstream 0.3.23 bugfix release

* Fri Apr 29 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.22-1
- Upstream 0.3.22 bugfix release

* Mon Apr 11 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.21-1
- Upstream 0.3.21 release

* Mon Feb 28 2011 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.21-0.a1
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

* Thu Aug 06 2009 Ricky Zhou <ricky@fedoraproject.org> - 0.3.15-1
- New release 0.3.15.
- Relicensed to LGPLv2+

* Mon Jul 27 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.14-1
- New release 0.3.14.

* Sat Jun 13 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.13.1-1
- Merge 0.3.12.1 and 0.3.13 releases together.

* Sat Jun 13 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.13-1
- New release.  Some new pkgdb API, defaultdict implementation, and a
  bugfix to response code from the shipped login controller.

* Thu Jun 11 2009 Ricky Zhou <ricky@fedoraproject.org> - 0.3.12.1-2
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

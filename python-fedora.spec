%if 0%{?fedora}
%global with_python3 1
%endif

%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2:        %global __python2 /usr/bin/python2}
%{!?python2_sitelib:  %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif
#%%global prerel c2

Name:           python-fedora
Version:        0.6.0
Release:        1%{?dist}
Summary:        Python modules for talking to Fedora Infrastructure Services

Group:          Development/Languages
License:        LGPLv2+
URL:            https://fedorahosted.org/python-fedora/
Source0:        https://fedorahosted.org/releases/p/y/%{name}/%{name}-%{version}%{?prerel}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
%if 0%{?rhel} && 0%{?rhel} <= 6
BuildRequires:  python-sphinx10
%else
BuildRequires:  python-sphinx
%endif
%if 0%{?fedora} || (0%{?rhel} == 6)
BuildRequires:  python-cherrypy2
%else
# Do not need TurboGears1 dependencies on epel7
%if 0%{?rhel} < 7
BuildRequires:  python-cherrypy
%endif
%endif
BuildRequires:  python-babel
BuildRequires:  TurboGears2
BuildRequires:  python-nose
BuildRequires:  python-kitchen
BuildRequires:  python-munch
# Needed for tests and for the way we build docs
%if 0%{?rhel} < 7
# Phasing this out.  First from epel7 and later for everything
BuildRequires: TurboGears
%endif
BuildRequires: python-repoze-who-friendlyform Django
BuildRequires: python-requests
BuildRequires: python-openid
BuildRequires: python-openid-teams
BuildRequires: python-openid-cla
BuildRequires: python-six

Requires:       python-simplejson
Requires:       python-munch
Requires:       python-kitchen
Requires:       python-requests
Requires:       python-beautifulsoup4
Requires:       python-six
# These are now optional dependencies.  Some bodhi methods will not work if
# they aren't installed but they aren't needed for most functionality of the
# module.
#Requires:       koji python-iniparse yum

%description
Python modules that help with building Fedora Services.  The client module
included here can be used to build programs that communicate with many of
Fedora Infrastructure's Applications such as Bodhi, PackageDB, MirrorManager,
and FAS2.

%if 0%{?with_python3}
%package -n python3-fedora
Summary:        Python modules for talking to Fedora Infrastructure Services
Group:          Development/Languages

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-sphinx
BuildRequires:  python3-babel
BuildRequires:  python3-nose
BuildRequires:  python3-kitchen
BuildRequires:  python3-munch

BuildRequires:  python3-requests
BuildRequires:  python3-openid
BuildRequires:  python3-six

Requires:       python3-simplejson
Requires:       python3-munch
Requires:       python3-kitchen
Requires:       python3-requests
Requires:       python3-beautifulsoup4
Requires:       python3-six

%description -n python3-fedora
Python modules that help with building Fedora Services.  The client module
included here can be used to build programs that communicate with many of
Fedora Infrastructure's Applications such as Bodhi, PackageDB, MirrorManager,
and FAS2.
%endif

%if 0%{?rhel} < 7
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
%endif

%package turbogears2
Summary: Python modules for TurboGears applications in Fedora Infrastructure
Group:          Development/Languages
License:        LGPLv2+
Requires: %{name} = %{version}-%{release}
Requires: TurboGears2
Requires: python-sqlalchemy
%if 0%{?fedora} || 0%{?rhel} >= 7
Requires: python-mako >= 0.3.6
%else
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

%if 0%{?with_python3}
rm -rf %{py3dir}
cp -a . %{py3dir}
%endif

%build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
## No docs, because that tries to hit the tg pathways (py2-only)
#%{__python3} setup.py build_sphinx
## We can probably port releaseutils.py, but we haven't yet.
#%{__python3} releaseutils.py build_catalogs
popd
%endif

%{__python2} setup.py build
%{__python2} setup.py build_sphinx
%{__python2} releaseutils.py build_catalogs

%install
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
## We can probably port releaseutils.py, but we haven't yet.
#DESTDIR=%{buildroot} %{__python3} releaseutils.py install_catalogs

# Remove regression tests
rm -rf %{buildroot}%{python3_sitelib}/fedora/wsgi/test
rm -rf %{buildroot}%{python3_sitelib}/tests/

popd
%endif

%{__python2} setup.py install --skip-build --root %{buildroot}
DESTDIR=%{buildroot} %{__python2} releaseutils.py install_catalogs

# Cleanup doc
mv build/sphinx/html doc/
if test -e doc/html/.buildinfo ; then
  rm doc/html/.buildinfo
fi
find doc -name 'EMPTY' -exec rm \{\} \;

# Remove regression tests
rm -rf %{buildroot}%{python2_sitelib}/fedora/wsgi/test
rm -rf %{buildroot}%{python2_sitelib}/tests/

%find_lang %{name}

%files -f %{name}.lang
%defattr(-,root,root,-)
%doc NEWS README COPYING AUTHORS doc
%{python2_sitelib}/fedora/
%{python2_sitelib}/python_fedora*egg-info
%exclude %{python2_sitelib}/fedora/tg/
%exclude %{python2_sitelib}/fedora/tg2/
%exclude %{python2_sitelib}/fedora/wsgi/
%exclude %{python2_sitelib}/fedora/django/
%exclude %{python2_sitelib}/flask_fas.py*
%exclude %{python2_sitelib}/flask_fas_openid.py*

%if 0%{?with_python3}
%files -f %{name}.lang -n python3-fedora
%defattr(-,root,root,-)
%doc NEWS README COPYING AUTHORS doc
%{python3_sitelib}/fedora/
%{python3_sitelib}/python_fedora*egg-info
%{python3_sitelib}/__pycache__/flask_fas*
%exclude %{python3_sitelib}/fedora/tg/
%exclude %{python3_sitelib}/fedora/tg2/
%exclude %{python3_sitelib}/fedora/wsgi/
%exclude %{python3_sitelib}/fedora/django/
%exclude %{python3_sitelib}/flask_fas.py*
%exclude %{python3_sitelib}/flask_fas_openid.py*
%endif

%if 0%{?rhel} < 7
%files turbogears
%{python2_sitelib}/fedora/tg/
%endif

%files turbogears2
%{python2_sitelib}/fedora/wsgi/
%{python2_sitelib}/fedora/tg2/

%files django
%{python2_sitelib}/fedora/django/

%files flask
%{python2_sitelib}/flask_fas.py*
%{python2_sitelib}/flask_fas_openid.py*

%changelog
* Fri Oct 09 2015 Ralph Bean <rbean@redhat.com> - 0.6.0-1
- Cache session cookies between use for clients using OpenID.
- Retry failed requests for clients using OpenID
- Remove Bodhi server version detection code.
- Python3 support for the BodhiClient.
- Drop support for python-requests-1.x

* Fri Sep 04 2015 Ralph Bean <rbean@redhat.com> - 0.5.6-1
- Python2.6 fix for el6.

* Thu Aug 27 2015 Ralph Bean <rbean@redhat.com> - 0.5.5-2
- Specbump for F21.  https://github.com/fedora-infra/bodhi/issues/363

* Wed Aug 19 2015 Ralph Bean <rbean@redhat.com> - 0.5.5-1
- Consistent exception handling in the Bodhi2Client.
- More adjustments to bodhi server version detection.

* Tue Aug 18 2015 Ralph Bean <rbean@redhat.com> - 0.5.4-1
- Adjust usage of python-six to be compatible with older versions on rhel7.
- More updates to detection of the bodhi server version.

* Tue Aug 18 2015 Ralph Bean <rbean@redhat.com> - 0.5.3-1
- Better compatibility with 'fedpkg update' for bodhi.

* Mon Aug 17 2015 Ralph Bean <rbean@redhat.com> - 0.5.2-1
- Better version checking against the bodhi server.

* Mon Aug 17 2015 Ralph Bean <rbean@redhat.com> - 0.5.1-1
- Typofix in the BodhiClient.

* Mon Aug 17 2015 Ralph Bean <rbean@redhat.com> - 0.5.0-1
- Bodhi2 compatibility.
- Return munch object from OpenIdBaseClient.
- Minor python3 fixes.

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.4.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Mon May 04 2015 Ralph Bean <rbean@redhat.com> - 0.4.0-2
- More specific directory ownership for the core packages.

* Tue Apr 28 2015 Ralph Bean <rbean@redhat.com> - 0.4.0-1
- Upstream release.
- python3 subpackages.
- New deps on python-munch and python-six.

* Sat Jan 24 2015 Xavier Lamien <laxathom@fedoraproject.org> - 0.3.37-1
- Upstream release.

* Thu Oct 23 2014 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.3.36-2
- Backport the flask-fas-openid fix merged upstream at:
  https://github.com/fedora-infra/python-fedora/pull/108

* Thu Aug  7 2014 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.36-1
- New upstream release fixing logging in openidbaseclient

* Wed Aug  6 2014 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.35-1
- Upstream 0.3.35 release that adds openidbaseclient

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.34-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri May  2 2014 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.34-1
- Upstream 0.3.34 release with security fixes for TG and flask services built
  with python-fedora

* Fri Mar 14 2014 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.33-3
- Do not build the TG1 subpackage on EPEL7.  Infrastructure is going to port
  its applications away from TG1 by the time they switch to RHEL7.  So we want
  to get rid of TurboGears1 packages before RHEL7.
- Fix conditionals so that they include the proper packages on epel7

* Fri Jan 10 2014 Dennis Gilmore <dennis@ausil.us> - 0.3.33-2
- clean up some rhel logic in the spec

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

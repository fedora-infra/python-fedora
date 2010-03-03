from tg import TGController, expose, require, redirect, flash, request, url
from tg import tmpl_context
from pylons.i18n import _
from repoze.what import predicates

class BaseController(TGController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        request.identity = request.environ.get('repoze.who.identity')
        tmpl_context.identity = request.identity
        return TGController.__call__(self, environ, start_response)


class RootController(BaseController):

    @expose('json')
    def index(self):
        return {'foo': 'bar'}

    @expose()
    @require(predicates.is_user('manager'))
    def secure(self):
        return u'Hello World!'

    @expose('fedora.wsgi.test.templates.login')
    def login(self, came_from=url('/')):
        """Start the user login."""
        login_counter = request.environ['repoze.who.logins']
        if login_counter > 0:
            flash(_('Wrong credentials'), 'warning')
        return dict(page='login', login_counter=str(login_counter),
                    came_from=came_from)

    @expose()
    def post_login(self, came_from=url('/')):
        """
        Redirect the user to the initially requested page on successful
        authentication or redirect her back to the login page if login failed.

        """
        if not request.identity:
            login_counter = request.environ['repoze.who.logins'] + 1
            redirect(url('/login', came_from=came_from, __logins=login_counter))
        userid = request.identity['repoze.who.userid']
        flash(_('Welcome back, %s!') % userid)
        redirect(came_from)

    @expose()
    def post_logout(self, came_from=url('/')):
        """
        Redirect the user to the initially requested page on logout and say
        goodbye as well.

        """
        flash(_('We hope to see you soon!'))
        redirect(came_from)

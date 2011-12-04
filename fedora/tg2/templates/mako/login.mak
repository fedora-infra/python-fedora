<%def name="loginform(message='')">
<div id="loginform" class="login">
  <h3><span>${_('Log In')}</span></h3>
  % if message:
    <p>${message}</p>
  % endif
  % if (request.identity and '_csrf_token' in request.identity) or request.environ.get('CSRF_AUTH_SESSION_ID'):
    <form action="${tg.url(came_from)}" method="post">
      <p><a href="http://en.wikipedia.org/wiki/CSRF">${_('CSRF attacks')}</a>
        ${_(''' are a means for a malicious website to make a request of another
        web server as the user who contacted the malicious web site.  The
        purpose of this page is to help protect your account and this server
        from attacks from such malicious web sites.  By clicking below, you are
        proving that you are a person rather than just the web browser
        forwarding your authentication cookies on behalf of a malicious
        website.''')}</p>
        <input type="submit" name="csrf_login" class="button"
          value="${_('I am a human')}" />
    </form>
  % else:
    <form action="${tg.url('/login_handler', params=dict(came_from=came_from.encode('utf-8'), __logins=login_counter.encode('utf-8')))}" method="post" accept-charset="UTF-8" class="loginfields">
      <label for="login">${_('Username:')}</label>
      <input type="text" id="login" name="login" class="text" />
      <br />
      <label for="password">${_('Password:')}</label>
      <input type="password" id="password" name="password" class="text" />
      <input type="submit" id="submit" class="button" value="${_('Login')}" />
    </form>
  % endif
  <ul>
    <li><a href="${tg.url(tg.config.get('fas.url', 'https://admin.fedoraproject.org/accounts').rstrip('/') + '/user/resetpass')}">${_('Forgot Password?')}</a></li>
    <li><a href="${tg.url(tg.config.get('fas.url', 'https://admin.fedoraproject.org/accounts').rstrip('/') + '/user/new')}">${_('Sign Up')}</a></li>
  </ul>
</div>
</%def>

<%def name="logintoolitem(href)">
% if request.identity:
  <li class="toolitem">
  ${_('Welcome')}
  % if href:
    <a href="${href}">
      % if hasattr(request.identity['user'], 'display_name'):
        ${request.identity['user'].display_name}
      % else:
        ${request.identity['user'].user_name}
      % endif
    </a>
  % else:
    % if hasattr(request.identity['user'], 'display_name'):
      ${request.identity['user'].display_name}
    % else:
      ${request.identity['user'].user_name}
    % endif
  % endif
  </li>

% elif not request.identity and not request.environ.get('CSRF_AUTH_SESSION_ID'):
  ## If not logged in and no sign that we just lack a csrf token, offer login
  <li id="login-toolitem" class="toolitem">
    ${_('You are not logged in')}
    <form action="${tg.url('/login/?came_from=%s' % tg.quote_plus('?'.join((request.environ.get('PATH_INFO', '/'), request.environ.get('QUERY_STRING')))))}" method="POST">
      <input type="submit" value="${_('Login')}" class="button" />
    </form>
  </li>
% elif not request.identity:
  ## Only CSRF_token missing
  <li id="login-toolitem" class="toolitem">
    ${_('CSRF protected')}
    ## Just go back to the present page using tg.url() to append the _csrf_token
    <form action="${tg.url('?'.join((request.environ.get('PATH_INFO', '/'), request.environ.get('QUERY_STRING'))))}" method="POST">
      <input type="submit" value="${_('Verify Login')}" class="button" />
    </form>
    </li>
% endif
% if request.identity or request.environ.get('CSRF_AUTH_SESSION_ID'):
  <li id="login-toolitem" class="toolitem">
  <form action="${tg.url('/logout_handler')}" method="POST">
    <input type="submit" value="${_('Logout')}" class="button" />
  </form>
  </li>
% endif
</%def>

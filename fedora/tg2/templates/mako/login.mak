<%def name="loginform(message='')">
<div id="loginform">
  <h2><span>Login</span></h2>
  % if message:
    <p>${message}</p>
  % endif
  % if (request.identity and '_csrf_token' in request.identity) or request.environ.get('CSRF_AUTH_SESSION_ID'):
    <form action="${tg.url(came_from)}" method="POST">
      <p><a href="http://en.wikipedia.org/wiki/CSRF">CSRF attacks</a>
        are a means for a malicious website to make a request of another
        web server as the user who contacted the malicious web site.  The
        purpose of this page is to help protect your account and this server
        from attacks from such malicious web sites.  By clicking below, you are
        proving that you are a person rather than just the web browser
        forwarding your authentication cookies on behalf of a malicious
        website.</p>
        <input type="submit" class="button"
          value="I am a human" />
    </form>
  % else:
    <form action="${tg.url('/login_handler', params=dict(came_from=came_from.encode('utf-8'), __logins=login_counter.encode('utf-8')))}" method="POST" class="loginfields">
      <label for="login">Username:</label><input type="text" id="login" name="login" class="text"></input><br/>
      <label for="password">Password:</label><input type="password" id="password" name="password" class="text"></input>
      <input type="submit" id="submit" value="Login" />
    </form>
  % endif
</div>
</%def>

<%def name="logintoolitem(href)">
% if request.identity:
  <li class="toolitem">
  ${_('Logged in:')}
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

<%def name="jsglobals()">
  <script type="text/javascript">
    if (typeof(fedora) == 'undefined') {
      fedora = {};
    }
    fedora.identity = {anonymous: true};
    /* Remove token and trailing slash */
    fedora.baseurl = "${tg.url('/')}".replace(/\/?(\?[^?]+)?$/, '');
  </script>
  % if request.identity:
    <script type="text/javascript">
      fedora.identity = {userid: "${request.identity['user'].user_id}",
        username: "${request.identity['user'].user_name}",
        display_name: "${request.identity['user'].display_name}",
      % if 'CSRF_TOKEN' in request.environ:
        token: "${request.environ['CSRF_TOKEN']}",
      % endif
        anonymous: false
      };
    </script>
  % endif
</%def>

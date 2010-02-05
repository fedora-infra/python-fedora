from tg import TGController, expose

class RootController(TGController):

    @expose('json')
    def index(self):
        return {'foo': 'bar'}

def do_monkeypatch():
    def get_url(self):
        return self._view.get_url('%s.%s' % (self._view.endpoint, self._view._default_view))

    import flask_admin.menu
    flask_admin.menu.MenuView.get_url = get_url
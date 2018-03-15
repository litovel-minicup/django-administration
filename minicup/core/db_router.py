# coding=utf-8


class DatabaseRouter(object):
    """
    A router to control all database operations on models in the
    auth application.
    """

    DB_NAME = 'minicup'

    def db_for_read(self, model, **hints):
        """
        Attempts to read auth models go to auth_db.
        """
        if model._meta.app_label == 'core':
            return self.DB_NAME
        return None

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the auth app is involved.
        """
        apps = {obj1._meta.app_label, obj2._meta.app_label}
        if len(apps) == 1:
            return True
        if 'core' in apps:
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the auth app only appears in the 'auth_db'
        database.
        """
        return app_label != 'core'

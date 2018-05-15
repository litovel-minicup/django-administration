# coding=utf-8


def configure_django():
    import django
    # env DJANGO_SETTINGS_MODULE should be set
    django.setup()

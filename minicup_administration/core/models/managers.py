# coding=utf-8


from django.db import models


class MatchQuerySet(models.QuerySet):
    def actual(self):
        return self.filter(category__year__actual=True)


class MatchManager(models.Manager):
    def get_queryset(self):
        return MatchQuerySet(self.model, using=self._db)

    def actual(self):
        return self.get_queryset().actual()

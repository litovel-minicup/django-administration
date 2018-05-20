# coding=utf-8
from typing import Union, Iterable

from django.db import models
from django.db.models import Q


class MatchQuerySet(models.QuerySet):
    def actual(self):
        return self.filter(category__year__actual=True)


class MatchManager(models.Manager):
    def get_queryset(self):
        return MatchQuerySet(self.model, using=self._db)

    def actual(self):
        return self.get_queryset().actual()

    def find_matches_with_required_timer(self) -> models.QuerySet:
        return self.filter(
            Q(
                online_state=self.model.STATE_HALF_FIRST,
                first_half_start__isnull=False,
            ) | Q(
                online_state=self.model.STATE_HALF_SECOND,
                second_half_start__isnull=False
            )
        )

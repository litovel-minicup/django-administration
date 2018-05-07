# coding=utf-8
import string
from random import choice
from uuid import uuid4

from django.core.management.base import BaseCommand

from minicup_administration.core.models import TeamInfo


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('year_slug', type=str)
        parser.add_argument('category_slug', type=str)

    def handle(self, *args, **options):
        category_slug = options.get('category_slug')
        year_slug = options.get('year_slug')

        teams = TeamInfo.objects.filter(
            category__slug=category_slug,
            category__year__slug=year_slug,
        )

        for team in teams:
            team.auth_token = uuid4()
            team.password = ''.join(choice(string.digits) for _ in range(6))
            print(team.slug, team.auth_token, team.password)
            team.save()

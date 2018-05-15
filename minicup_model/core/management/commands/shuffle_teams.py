# coding=utf-8
from random import shuffle

from django.core.management.base import BaseCommand

from minicup_model.core.models import Match


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('category_id', type=int)

    def handle(self, *args, **options):
        category_id = options.get('category_id')

        matches = Match.objects.filter(category__id=category_id)

        for match in matches:
            teams = [match.home_team_info, match.away_team_info]
            shuffle(teams)
            match.home_team_info, match.away_team_info = teams
            match.save()

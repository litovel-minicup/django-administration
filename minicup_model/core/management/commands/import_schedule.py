# coding=utf-8
import string
from datetime import date, datetime
from random import choice
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from minicup_model.core.models import TeamInfo, Category, MatchTerm, Day, Match, Team


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('year_slug', type=str)
        parser.add_argument('category_slug', type=str)
        parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        category_slug = options.get('category_slug')
        year_slug = options.get('year_slug')
        to_import = open(options.get('file'))

        category = Category.objects.get(
            slug=category_slug,
            year__slug=year_slug
        )
        category.match_category.all().delete()
        # category.category_team.all().delete()

        for line in to_import.readlines():
            line = line.strip().split('\t')
            if not line:
                continue
            # separator is \t
            # 12.6.2018 13:30 Tatran Dukla A
            day, time, home, away, location = line

            home, _ = TeamInfo.objects.get_or_create(
                name=home,
                category=category,
                defaults=dict(
                    slug=slugify(home)
                )
            )
            Team.objects.get_or_create(
                team_info=home,
                category=home.category,
                actual=1
            )
            away, _ = TeamInfo.objects.get_or_create(
                name=away,
                category=category,
                defaults=dict(
                    slug=slugify(away)
                )
            )
            Team.objects.get_or_create(
                team_info=away,
                category=away.category,
                actual=1
            )
            day = datetime.strptime(day.strip(), "%d.%m.%Y").date()
            time = datetime.strptime(time.strip(), "%H:%M")
            day, _ = Day.objects.get_or_create(
                year=category.year,
                day=day
            )
            term, _ = MatchTerm.objects.get_or_create(
                day=day,
                start=time,
                end=(time + MatchTerm.STANDARD_LENGTH),
                location=location,
            )
            print(term, home, away)
            Match(
                match_term=term,
                home_team_info=home,
                away_team_info=away,
                category=category,

            ).save()





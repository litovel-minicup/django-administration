# coding=utf-8
from datetime import timedelta, datetime

from django.core.management.base import BaseCommand
from django.db.models import F

from minicup_model.core.models import MatchTerm, Category, Match


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('day', type=str)

    def handle(self, *args, **options):
        day = datetime.strptime(options.get('day').strip(), "%d.%m.%Y").date()
        year = day.year

        inside = Category.objects.get(slug='mladsi', year__slug=str(year))  # from A,B -> A
        outside = Category.objects.get(slug='starsi', year__slug=str(year))  # from C,D -> B

        inside_matches = Match.objects.filter(
            category=inside,
            match_term__day__day=day,
            confirmed__isnull=True,
        )

        for a_match in inside_matches.filter(match_term__location='A'):
            a_match.match_term.end -= timedelta(minutes=15)
            a_match.match_term.save()

        for b_match in inside_matches.filter(match_term__location='B'):
            b_match.match_term.start += timedelta(minutes=15)
            b_match.match_term.location = 'A'
            b_match.match_term.save()

        outside_matches = Match.objects.filter(
            category=outside,
            match_term__day__day=day,
            confirmed__isnull=True,
        )

        for c_match in outside_matches.filter(match_term__location='C'):
            c_match.match_term.end -= timedelta(minutes=15)
            c_match.match_term.location = 'B'
            c_match.match_term.save()
        for c_match in outside_matches.filter(match_term__location='D'):
            c_match.match_term.start += timedelta(minutes=15)
            c_match.match_term.location = 'B'
            c_match.match_term.save()

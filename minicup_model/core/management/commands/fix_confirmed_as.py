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

    def handle(self, *args, **options):
        category_slug = options.get('category_slug')
        year_slug = options.get('year_slug')

        category = Category.objects.get(
            slug=category_slug,
            year__slug=year_slug
        )
        print(category.match_category.filter(confirmed__isnull=False).order_by('confirmed_as').count())


        for index, match in enumerate(category.match_category.filter(confirmed__isnull=False).order_by('confirmed_as'), start=1):
            match.confirmed_as = index
            match.save()



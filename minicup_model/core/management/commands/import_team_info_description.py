# coding=utf-8
from typing import Optional

from django.core.management.base import BaseCommand

from minicup_model.core.models import TeamInfo, Category

DESCRIPTION_TEMPLATE = """
účasti: {}
úspěchy: {}
zajímavosti: {}
klub: {}
tip: {}
"""


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

        for line in to_import.readlines():
            line = line.strip().split('\t')
            if not line:
                continue
            # separator is \t
            # 12.6.2018 13:30 Tatran Dukla A
            name, abbr, *data = line

            description = DESCRIPTION_TEMPLATE.format(*data)

            team_info = TeamInfo.objects.filter(
                category=category,
                name=name
            ).first()  # type: Optional[TeamInfo]

            if not team_info:
                print('Skipping {}, not found.'.format(name))
                continue

            team_info.description = description
            team_info.save(update_fields=['description'])

# coding=utf-8
import logging
from datetime import timedelta
from typing import Tuple

from django.db import models
from django.utils.translation import ugettext as _

from minicup_administration.core.models.managers import MatchManager


class Category(models.Model):
    year = models.ForeignKey('Year', models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=30)
    slug = models.CharField(max_length=30)
    default = models.IntegerField()

    def __str__(self):
        return '{}'.format(self.name or self.slug)

    class Meta:
        managed = False
        db_table = 'category'
        unique_together = (('year', 'slug'),)
        ordering = ['year', 'slug']


class Day(models.Model):
    day = models.DateField()
    year = models.ForeignKey('Year', models.PROTECT)

    def __str__(self):
        return _('{}. {}. {}').format(self.day.day, self.day.month, self.year)

    class Meta:
        managed = False
        db_table = 'day'


class DbMigrations(models.Model):
    version = models.CharField(primary_key=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'db_migrations'


class Match(models.Model):
    STATE_INIT = 'init'
    STATE_HALF_FIRST = 'half_first'
    STATE_HALF_PAUSE = 'pause'
    STATE_HALF_SECOND = 'half_second'
    STATE_END = 'end'

    STATES = {
        STATE_INIT: (STATE_HALF_FIRST,),
        STATE_HALF_FIRST: (STATE_HALF_PAUSE,),
        STATE_HALF_PAUSE: (STATE_HALF_SECOND,),
        STATE_HALF_SECOND: (STATE_END,),
        STATE_END: ()
    }

    DEFAULT_STATES = (STATE_INIT, STATE_END)  # by by bool(match.confirmed)

    HALF_LENGTH = timedelta(minutes=10)

    match_term = models.ForeignKey('MatchTerm', models.PROTECT, blank=True, null=True)
    category = models.ForeignKey(Category, models.PROTECT)
    home_team_info = models.ForeignKey('TeamInfo', models.PROTECT, related_name='match_home_team_info')
    away_team_info = models.ForeignKey('TeamInfo', models.PROTECT, related_name='match_away_team_info')
    score_home = models.IntegerField(blank=True, null=True)
    score_away = models.IntegerField(blank=True, null=True)
    confirmed = models.DateTimeField(blank=True, null=True)
    confirmed_as = models.IntegerField(blank=True, null=True)
    online_state = models.CharField(max_length=255, choices=STATES.items())

    first_half_start = models.DateTimeField(blank=True, null=True)
    second_half_start = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return _('{} vs. {}').format(self.home_team_info, self.away_team_info)

    class Meta:
        managed = False
        db_table = 'match'
        unique_together = (('category', 'home_team_info', 'away_team_info'),)
        ordering = ('match_term__day__day', 'match_term__start')

    def serialize(self, **kwargs):
        return dict(
            id=self.id,
            home_team_name=self.home_team_info.name,
            away_team_name=self.away_team_info.name,
            home_team_color='#ff8574',
            away_team_color='#88dd12',
            first_half_start=self.first_half_start.timestamp() if self.first_half_start else None,
            second_half_start=self.second_half_start.timestamp() if self.second_half_start else None,
            score=[self.score_home, self.score_away],
            state=self.online_state or (self.STATE_END if self.confirmed else self.STATE_INIT),
            **kwargs
        )

    @property
    def teams(self) -> Tuple["TeamInfo", "TeamInfo"]:
        return self.home_team_info, self.away_team_info

    def change_state(self, state: str) -> bool:
        if state not in self.STATES:
            logging.error('Unknown state {} to set.'.format(state))
            return False

        if state not in self.STATES.get(self.online_state, self.DEFAULT_STATES[bool(self.confirmed)]):
            logging.error('Cannot go from {} to {}.'.format(self.online_state, state))
            return False

        logging.info('Changing match state from {} to {}.'.format(self.online_state, state))
        self.online_state = state
        self.save(update_fields=('online_state',))
        return True


class MatchEvent(models.Model):
    match = models.ForeignKey(Match, models.PROTECT, related_name='match_match_event')
    score_home = models.IntegerField(blank=True, null=True)
    score_away = models.IntegerField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16, blank=True, null=True)
    half_index = models.IntegerField()
    time_offset = models.IntegerField()
    player = models.ForeignKey('Player', models.PROTECT, blank=True, null=True)
    team_info = models.ForeignKey('TeamInfo', models.PROTECT, blank=True, null=True)

    TYPE_START = 'start'
    TYPE_GOAL = 'goal'
    TYPE_END = 'end'
    TYPE_INFO = 'info'

    HALF_INDEX_FIRST = 0
    HALF_INDEX_SECOND = 1

    class Meta:
        managed = False
        db_table = 'match_event'
        ordering = ['half_index', 'time_offset']

    def serialize(self):
        return dict(
            id=self.id,
            timeOffset=self.time_offset,
            halfIndex=self.half_index,
            message=self.message,
            score=self.score,
            type=self.type
        )

    @property
    def score(self) -> Tuple[int, int]:
        return self.score_home or 0, self.score_away or 0

    def __str__(self):
        return '{}-{}-{}'.format(
            self.type,
            self.match,
            self.player or self.team_info or '.'
        )


class MatchTerm(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    day = models.ForeignKey(Day, models.PROTECT)
    location = models.CharField(max_length=50)

    def __str__(self):
        return _('{} | {}').format(self.start.time(), self.day)

    class Meta:
        managed = False
        db_table = 'match_term'
        ordering = ('day', 'start')


class News(models.Model):
    title = models.TextField()
    content = models.TextField()
    updated = models.DateTimeField()
    added = models.DateTimeField()
    year = models.ForeignKey('Year', models.PROTECT, blank=True, null=True)
    texy = models.IntegerField()
    tag = models.ForeignKey('Tag', models.PROTECT, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'news'


class Photo(models.Model):
    filename = models.TextField()
    added = models.DateTimeField()
    taken = models.DateTimeField()
    active = models.IntegerField()
    year = models.ForeignKey('Year', models.PROTECT, blank=True, null=True)
    author = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'photo'


class PhotoTag(models.Model):
    photo = models.ForeignKey(Photo, models.PROTECT, primary_key=True, related_name='photo_tag_photo')
    tag = models.ForeignKey('Tag', models.PROTECT, related_name='photo_tag_tag')

    class Meta:
        managed = False
        db_table = 'photo_tag'
        unique_together = (('photo', 'tag'),)


class Player(models.Model):
    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    number = models.IntegerField()
    secondary_number = models.IntegerField(blank=True, null=True)
    team_info = models.ForeignKey('TeamInfo', models.PROTECT, related_name='team_info_player')

    class Meta:
        managed = False
        db_table = 'player'
        ordering = ['secondary_number', 'number']

    def __str__(self):
        return '{0.name} {0.surname}'.format(self)


class StaticContent(models.Model):
    slug = models.CharField(max_length=50)
    content = models.TextField()
    updated = models.DateTimeField(blank=True, null=True)
    year = models.ForeignKey('Year', models.PROTECT, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'static_content'


class Tag(models.Model):
    name = models.CharField(max_length=50, blank=True, null=True)
    slug = models.CharField(max_length=50)
    is_main = models.IntegerField()
    main_photo = models.ForeignKey(Photo, models.PROTECT, blank=True, null=True)
    year = models.ForeignKey('Year', models.PROTECT, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tag'
        unique_together = (('name', 'year'), ('slug', 'year'),)

    def __str__(self):
        return _('Tag {}:{}').format(self.year, self.name)


class Team(models.Model):
    objects = MatchManager()

    category = models.ForeignKey(Category, models.PROTECT)
    team_info = models.ForeignKey('TeamInfo', models.PROTECT)
    order = models.IntegerField()
    points = models.IntegerField()
    scored = models.IntegerField()
    received = models.IntegerField()
    inserted = models.DateTimeField()
    actual = models.IntegerField()
    after_match = models.ForeignKey(Match, models.PROTECT, blank=True, null=True)

    def __str__(self):
        return _('Team record for {}').format(self.team_info)

    class Meta:
        managed = False
        db_table = 'team'


class TeamInfo(models.Model):
    category = models.ForeignKey(Category, models.PROTECT)
    name = models.CharField(max_length=30)
    slug = models.CharField(max_length=30)
    static_content = models.ForeignKey(StaticContent, models.PROTECT, blank=True, null=True)
    tag = models.ForeignKey(Tag, models.PROTECT, blank=True, null=True, related_name='team_info_tag')

    dress_color = models.CharField(max_length=6, blank=True, null=True)
    dress_color_secondary = models.CharField(max_length=6)
    trainer_name = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    password = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    auth_token = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'team_info'
        unique_together = (('category', 'slug'), ('category', 'name'),)


class User(models.Model):
    username = models.TextField()
    password_hash = models.TextField()
    fullname = models.TextField()

    class Meta:
        managed = False
        db_table = 'user'


class Year(models.Model):
    year = models.TextField()  # This field type is a guess.
    name = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=20)
    actual = models.IntegerField()

    def __str__(self):
        return _('{}').format(self.name or self.slug)

    class Meta:
        managed = False
        db_table = 'year'


__all__ = [
    'MatchEvent',
    'Match',
    'MatchTerm',
    'Player',
    'TeamInfo',
    'Category',
    'Team',
    'News',
    'Day',
    'Photo',
    'PhotoTag',
    'Tag',
    'StaticContent',
    'User',
    'Year',
]

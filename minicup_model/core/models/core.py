# coding=utf-8
import logging
from datetime import timedelta, datetime
from typing import Tuple, Optional

from django.db import models
from django.db.models import Func, CharField, F, Value, DateTimeField
from django.db.models.functions import Cast, TruncDate, TruncTime
from django.utils.translation import ugettext as _
from django_extensions.db.fields import CreationDateTimeField

from minicup_model.core.models.managers import MatchManager


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
    MATCH_START_ANNOTATION = Cast(
        Func(
            TruncDate(F('match_term__day__day')),
            Value('  ', output_field=CharField()),
            TruncTime(F('match_term__start')),
            output_field=CharField(),
            function='CONCAT',
        ), output_field=DateTimeField()
    )

    objects = MatchManager()

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

    MATCH_PLAYING_STATE = (STATE_HALF_FIRST, STATE_HALF_PAUSE, STATE_HALF_SECOND)

    DEFAULT_STATES = (STATE_INIT, STATE_END)  # by by bool(match.confirmed)

    HALF_LENGTH = timedelta(minutes=10)

    match_term = models.ForeignKey('MatchTerm', models.PROTECT, blank=True, null=True, related_name='match_match_term')
    category = models.ForeignKey(Category, models.PROTECT, related_name='match_category')
    home_team_info = models.ForeignKey('TeamInfo', models.PROTECT, related_name='match_home_team_info')
    away_team_info = models.ForeignKey('TeamInfo', models.PROTECT, related_name='match_away_team_info')
    score_home = models.IntegerField(blank=True, null=True)
    score_away = models.IntegerField(blank=True, null=True)
    confirmed = models.DateTimeField(blank=True, null=True)
    confirmed_as = models.IntegerField(blank=True, null=True)
    online_state = models.CharField(max_length=255, choices=STATES.items())

    first_half_start = models.DateTimeField(blank=True, null=True)
    second_half_start = models.DateTimeField(blank=True, null=True)
    facebook_video_id = models.TextField(null=True, blank=True)

    def __str__(self):
        return _('{} vs. {}').format(self.home_team_info, self.away_team_info)

    class Meta:
        managed = False
        db_table = 'match'
        unique_together = (('category', 'home_team_info', 'away_team_info'),)
        ordering = ('match_term__day__day', 'match_term__start', 'match_term__location', 'id')

    def serialize(self, **kwargs):
        def format_color(team: "TeamInfo"):
            if team.dress_color_secondary:
                return '{t.dress_color} / {t.dress_color_secondary}'.format(t=team)
            return team.dress_color

        return dict(
            id=self.id,
            home_team_id=self.home_team_info.id,
            home_team_name=self.home_team_info.name,
            home_team_abbr=self.home_team_info.abbr or self.home_team_info.name[:4].upper(),
            home_team_slug=self.home_team_info.slug,
            home_team_color='#ff8574',
            home_team_color_name=format_color(self.home_team_info),

            away_team_id=self.away_team_info.id,
            away_team_name=self.away_team_info.name,
            away_team_abbr=self.away_team_info.abbr or self.away_team_info.name[:4].upper(),
            away_team_slug=self.away_team_info.slug,
            away_team_color='#88dd12',
            away_team_color_name=format_color(self.away_team_info),

            category_name=self.category.name,
            category_slug=self.category.slug,
            year_slug=self.category.year.slug,
            first_half_start=self.first_half_start.timestamp() if self.first_half_start else None,
            second_half_start=self.second_half_start.timestamp() if self.second_half_start else None,
            score=[self.score_home, self.score_away],
            confirmed=self.confirmed.timestamp() if self.confirmed else None,
            half_length=self.HALF_LENGTH.total_seconds(),
            state=self.online_state or (self.STATE_END if self.confirmed else self.STATE_INIT),
            facebook_video_id=self.facebook_video_id,
            match_term_start=self.match_term.timestamp,
            **kwargs
        )

    @property
    def teams(self) -> Tuple["TeamInfo", "TeamInfo"]:
        return self.home_team_info, self.away_team_info

    def change_state(self, new_state: str) -> Optional["MatchEvent"]:
        self.refresh_from_db()

        if new_state not in self.STATES:
            logging.error('MATCH {}: Unknown state {} to set.'.format(self.id, new_state))
            return

        if new_state not in self.STATES.get(self.online_state, self.DEFAULT_STATES[bool(self.confirmed)]):
            # logging.error('Cannot go from {} to {}.'.format(self.online_state, new_state))
            return

        logging.info('MATCH {}: Match state change from {} to {}.'.format(self.id, self.online_state, new_state))
        old_state = self.online_state
        self.online_state = new_state
        self.save(update_fields=('online_state',))

        event = MatchEvent(match=self)
        if not old_state or old_state == self.STATE_INIT:
            event.type = MatchEvent.TYPE_START
            event.half_index = event.time_offset = 0
            self.score_away = self.score_home = 0
            self.save(update_fields=('score_home', 'score_away',))
        elif old_state == self.STATE_HALF_FIRST:
            event.type = MatchEvent.TYPE_END
            event.half_index = 0
            event.time_offset = Match.HALF_LENGTH.total_seconds()
        elif old_state == self.STATE_HALF_PAUSE:
            event.type = MatchEvent.TYPE_START
            event.half_index = 1
            event.time_offset = 0
        elif old_state == self.STATE_HALF_SECOND:
            event.type = MatchEvent.TYPE_END
            event.half_index = 1
            event.time_offset = Match.HALF_LENGTH.total_seconds()
        else:
            raise RuntimeError('Never happen: {} -> {}.'.format(old_state, new_state))
        event.save()
        return event

    def on_timer_end(self) -> Optional['MatchEvent']:
        self.refresh_from_db()
        event = None
        if self.online_state == Match.STATE_HALF_FIRST:
            event = self.change_state(Match.STATE_HALF_PAUSE)
        elif self.online_state == Match.STATE_HALF_SECOND:
            event = self.change_state(Match.STATE_END)

        return event


class MatchEvent(models.Model):
    # id = models.IntegerField(primary_key=True, unique=True)
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

    @property
    def absolute_time(self):
        return ((self.match.first_half_start, self.match.second_half_start)[
                              self.half_index
                          ] + timedelta(seconds=self.time_offset))

    def serialize(self):
        try:
            team_index = self.match.teams.index(self.team_info)
        except ValueError:
            team_index = -1

        return dict(
            id=self.id,
            time_offset=self.time_offset,
            half_index=self.half_index,
            message=self.message,
            score=self.score,
            type=self.type,
            team_index=team_index,
            player_name=str(self.player) if self.player else None,
            player_number=self.player.number if self.player else None,

            absolute_time=self.absolute_time.timestamp()
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
    STANDARD_LENGTH = timedelta(minutes=30)

    start = models.DateTimeField()
    end = models.DateTimeField()
    day = models.ForeignKey(Day, models.PROTECT)
    location = models.CharField(max_length=50)

    def __str__(self):
        return _('{}{} | {}').format(
            '{} |'.format(self.location) if self.location else '',
            self.start.time(),
            self.day
        )

    @property
    def timestamp(self):
        return datetime.combine(self.day.day, self.start.time()).timestamp()

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

    def serialize(self):
        return dict(
            id=self.id,
            name=str(self),
            surname=self.surname,
            lastname=self.name,
            number=self.number
        )


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
    category = models.ForeignKey(Category, models.PROTECT, related_name='category_team')
    team_info = models.ForeignKey('TeamInfo', models.PROTECT)
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    scored = models.IntegerField(default=0)
    received = models.IntegerField(default=0)
    inserted = CreationDateTimeField()
    actual = models.IntegerField(default=0)
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
    abbr = models.CharField(max_length=4, null=True, blank=True)
    static_content = models.ForeignKey(StaticContent, models.PROTECT, blank=True, null=True)
    tag = models.ForeignKey(Tag, models.PROTECT, blank=True, null=True, related_name='team_info_tag')

    dress_color = models.CharField(max_length=6, blank=True, null=True)
    dress_color_secondary = models.CharField(max_length=6)
    trainer_name = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    password = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    auth_token = models.CharField(max_length=255)

    dress_color_min = models.CharField(max_length=7)
    dress_color_max = models.CharField(max_length=7)
    dress_color_secondary_min = models.CharField(max_length=7)
    dress_color_secondary_max = models.CharField(max_length=7)

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
    pin = models.TextField(blank=True, null=True)

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

# coding=utf-8
from random import choice, shuffle

from django.core.management.base import BaseCommand

from minicup_live_service.service.match_event import MatchEventMessageGenerator
from minicup_model.core.models import Match, MatchEvent, Player


class Command(BaseCommand):

    message_generator = MatchEventMessageGenerator()

    def add_arguments(self, parser):
        parser.add_argument('match_id', type=int)

    def handle(self, *args, **options):
        match_id = options.get('match_id')

        match = Match.objects.get(pk=match_id)
        print(match.home_team_info.name, match.away_team_info.name, match.score_home, match.score_away)

        if not match.confirmed:
            print('Cannot import to not confirmed match.')
            return

        if match.match_match_event.exists():
            print('Cannot import match with match event.')
            return

        print(match.home_team_info.name, ':')
        home_mapped = dict()
        line = input()
        while line:
            player_number, count = line.split()
            home_mapped[int(player_number)] = int(count)
            line = input()

        print(match.away_team_info.name, ':')
        away_mapped = dict()
        line = input()
        while line:
            player_number, count = line.split()
            away_mapped[int(player_number)] = int(count)
            line = input()

        # generate lists to random pick
        home_goals, away_goals = list(), list()
        for player_number, count in home_mapped.items():
            for _ in range(count):
                home_goals.append(player_number)
        for player_number, count in away_mapped.items():
            for _ in range(count):
                away_goals.append(player_number)

        if len(home_goals) != match.score_home:
            print('Invalid home count, {} != {}'.format(len(home_goals), match.score_home))
            return
        if len(away_goals) != match.score_away:
            print('Invalid away count, {} != {}'.format(len(away_goals), match.score_away))
            return

        shuffle(away_goals)
        shuffle(home_goals)

        score = [0, 0]
        time_offset = 0
        time_diff = ((Match.HALF_LENGTH * 2) / (match.score_away + match.score_home)).total_seconds()

        MatchEvent(
            match=match,
            type=MatchEvent.TYPE_START,
            half_index=0,
            time_offset=0,
        ).save()


        MatchEvent(
            match=match,
            type=MatchEvent.TYPE_START,
            half_index=1,
            time_offset=0,
        ).save()

        while home_goals or away_goals:
            if not home_goals:
                player_number = away_goals.pop()
                team_index = 1
            elif not away_goals:
                player_number = home_goals.pop()
                team_index = 0
            else:
                team_index = choice((0, 1))
                player_number = (home_goals, away_goals)[team_index].pop()

            score[team_index] += 1
            player = Player.objects.filter(
                number=player_number,
                team_info=(match.home_team_info, match.away_team_info)[team_index]
            ).first() if player_number else None

            me = MatchEvent(
                match=match,
                score_home=score[0],
                score_away=score[1],
                team_info=(match.home_team_info, match.away_team_info)[team_index],
                type=MatchEvent.TYPE_GOAL,
                time_offset=time_offset % Match.HALF_LENGTH.total_seconds(),
                half_index=time_offset // Match.HALF_LENGTH.total_seconds(),
                player=player,
            )
            me.save()
            me.message = self.message_generator.generate(me)
            me.save()
            time_offset += time_diff
        MatchEvent(
            match=match,
            type=MatchEvent.TYPE_END,
            half_index=0,
            time_offset=Match.HALF_LENGTH.total_seconds(),
        ).save()
        MatchEvent(
            match=match,
            type=MatchEvent.TYPE_END,
            half_index=1,
            time_offset=Match.HALF_LENGTH.total_seconds(),
        ).save()

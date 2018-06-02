import json

from django.db import models as m
from django.utils import timezone


class Player(m.Model):
    id = m.CharField(max_length=100, unique=True, primary_key=True)
    name = m.CharField(max_length=50, db_index=True)
    # slug = m.SlugField(max_length=50)
    # name = m.SlugField(max_length=50)
    shard = m.CharField('region', max_length=10)
    elo = m.PositiveSmallIntegerField(default=0)  # 0 to 32767
    tier = m.PositiveSmallIntegerField(default=0)
    wins = m.PositiveIntegerField(default=0)

    last_searched_matches_at = m.DateTimeField(
        'last time searched for matches', default=timezone.now)

    def __str__(self):
        return self.name


class Match(m.Model):
    players = m.ManyToManyField(Player)

    id = m.CharField(max_length=100, unique=True, primary_key=True)
    datetime = m.DateTimeField('when a match is created')
    mode = m.CharField(max_length=50)
    version = m.CharField(max_length=10)
    # has two rosters.

    def __str__(self):
        return self.mode


class Roster(m.Model):
    match = m.ForeignKey(Match, on_delete=m.CASCADE)

    id = m.CharField(max_length=100, unique=True, primary_key=True)
    team_kill_score = m.PositiveSmallIntegerField(default=0)
    side = m.CharField(max_length=10)
    turret_kill = m.PositiveSmallIntegerField(default=0)
    turret_remain = m.PositiveSmallIntegerField(default=0)
    # has 3 participants.

    def __str__(self):
        return self.side


class Participant(m.Model):
    player = m.ForeignKey(Player, on_delete=m.PROTECT)
    match = m.ForeignKey(Match, on_delete=m.PROTECT)
    roster = m.ForeignKey(Roster, on_delete=m.PROTECT)

    id = m.CharField(max_length=100, unique=True, primary_key=True)
    shard = m.CharField('region', max_length=10)
    kills = m.PositiveSmallIntegerField(default=0)
    deaths = m.PositiveSmallIntegerField(default=0)
    assists = m.PositiveSmallIntegerField(default=0)
    # kda
    gold = m.PositiveSmallIntegerField(default=0)
    farm = m.PositiveSmallIntegerField(default=0)
    items = m.CharField(max_length=200)
    tier = m.CharField(max_length=10)
    won = m.BooleanField()

    actor = m.CharField(max_length=50)

    def __str__(self):
        return self.actor

    def list_items(self):
        return json.loads(self.items)

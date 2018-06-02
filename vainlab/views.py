from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic

from .models import Player
from .vain_api import VainAPI


def index(request, ):
    return render(request, 'vainlab/index.html', )


class PlayerView(generic.DetailView):
    model = Player
    slug_field = 'name'
    template_name = 'vainlab/player.html'

    def get_queryset(self):
        return Player.objects


class PlayersView(generic.ListView):
    template_name = 'vainlab/players.html'
    context_object_name = 'top_players_list'

    def get_queryset(self):
        return Player.objects.filter(
            elo__gte=1600
        ).order_by('-elo')[:10]


def player_matches(request, name):
    err = None
    if not Player.objects.filter(name=name).exists():
        err = VainAPI().player_matches('ea', name)
    if not err:
        player = Player.objects.get(name=name)
        matches = player.match_set.all().order_by('-datetime')[:50]

        return render(request, 'vainlab/player_matches.html', {'player': player, 'matches': matches})
    return render(request, 'vainlab/player_matches.html', {'error': err})

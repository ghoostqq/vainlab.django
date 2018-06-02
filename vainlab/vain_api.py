import json
import os

import requests

from .models import Match, Participant, Player, Roster

# from .models import Item, Match, Participant, Player, Roster

SHARDS = ['ea', 'na', 'sg', 'eu', 'sa', 'cn']
MODE_JA = {
    'casual':                           'カジュアル',
    'ranked':                           'ランク',
    'casual_aral':                      '大乱闘',
    'blitz_pvp_ranked':                 '電撃',
    'blitz_rounds_pvp_casual':          'ガチンコ',
    'private':                          'プラベカジュ',
    'private_party_draft_match':        'プラベドラフト',
    'private_party_aral_match':         'プラベ大乱闘',
    'private_party_blitz_match':        'プラベ電撃',
    'private_party_blitz_rounds_match': 'プラベガチンコ',
    '5v5_pvp_casual':                   '5V5カジュ',
}


class VainAPI:
    ''' vainglory api '''

    def __init__(self):
        self.apikey = os.getenv("VAIN_APIKEY", "")
        self.apikey_crawl = os.getenv("VAIN_APIKEY_CRAWL", "")

    def request(self, url, params):
        headers = {
            'Authorization': self.apikey,
            'X-TITLE-ID': 'semc-vainglory',
            'Accept': 'application/vnd.api+json',
            # 'Accept-Encoding': 'gzip',
        }
        return requests.get(url, headers=headers, params=params).json()

    def single_player(self, reg, ign):
        url = f'https://api.dc01.gamelockerapp.com/shards/{reg}/players'
        params = {
            'filter[playerNames]': [ign],
        }
        res = self.request(url, params)
        if res.get('errors', ''):
            wrapped = res
        else:
            _attributes = res['data'][0]['attributes']
            wrapped = {
                'id': res['data'][0]['id'],
                'time': _attributes['createdAt'],
                'shrd': _attributes['shardId'],
                'name': _attributes['name'],
                'elo8': _attributes['stats']['elo_earned_season_8'],
                'wstr': _attributes['stats']['winStreak'],
                'lstr': _attributes['stats']['lossStreak'],
                'wins': _attributes['stats']['wins'],
                'tier': _attributes['stats']['skillTier'],
                'rnkp': _attributes['stats']['rankPoints']['ranked'],
                'blzp': _attributes['stats']['rankPoints']['blitz'],
            }
        return wrapped

    def player_matches(self, reg, ign):
        url = f'https://api.dc01.gamelockerapp.com/shards/{reg}/matches'
        params = {
            'filter[playerNames]': [ign],
            'sort': '-createdAt',
        }
        res = self.request(url, params)

        # ===============
        # Exit if error
        # ===============
        if res.get('errors', ''):
            return res

        # ===============
        # Save to DB
        # ===============

        # No need to do this beneath because using ManyToManyField requires saving first.
        # ~-~-~-
        # ro2m = dict()
        # for i in res['data']:
        #     for roster in i['relationships']['rosters']['data']:
        #         ro2m[roster['id']] = i['id']
        # pa2r = dict()
        # pl2p = dict()
        # for i in res['included']:
        #     if i['type'] == 'roster':
        #         for participant in i['relationships']['participants']['data']:
        #             pa2r[participant['id']] = i['id']
        #     if i['type'] == 'participant':
        #         player = i['relationships']['player']['data']['id']
        #         pl2p[player['id']] = i['id']

        matches = list()
        ro2m = dict()
        # Match
        for i in res['data']:
            match = Match(
                id=i['id'],
                datetime=i['attributes']['createdAt'],
                mode=i['attributes']['gameMode'],
                version=i['attributes']['patchVersion'],
            )
            match.save()
            matches.append(match)
            for roster in i['relationships']['rosters']['data']:
                ro2m[roster['id']] = i['id']
        pa2r = dict()
        # Roster -> Match
        for i in res['included']:
            if i['type'] == 'roster':
                r = Roster(
                    id=i['id'],
                    team_kill_score=i['attributes']['stats']['heroKills'],
                    side=i['attributes']['stats']['side'],
                    turret_kill=i['attributes']['stats']['turretKills'],
                    turret_remain=i['attributes']['stats']['turretsRemaining'],
                    match_id=ro2m[i['id']],
                )
                r.save()
                for participant in i['relationships']['participants']['data']:
                    pa2r[participant['id']] = i['id']
        # Player
        for i in res['included']:
            if i['type'] == 'player':
                p = Player(
                    id=i['id'],
                    name=i['attributes']['name'],
                    # slug=i['attributes']['name'],
                    shard=i['attributes']['shardId'],
                    elo=i['attributes']['stats']['rankPoints']['ranked'],
                    tier=i['attributes']['stats']['skillTier'],
                    wins=i['attributes']['stats']['wins'],
                )
                p.save()
        # Participant -> Roster, Player
        for i in res['included']:
            if i['type'] == 'participant':
                p = Participant(
                    id=i['id'],
                    actor=i['attributes']['actor'],
                    shard=i['attributes']['shardId'],
                    kills=i['attributes']['stats']['kills'],
                    deaths=i['attributes']['stats']['deaths'],
                    assists=i['attributes']['stats']['assists'],
                    # kda
                    gold=i['attributes']['stats']['gold'],
                    farm=i['attributes']['stats']['farm'],
                    items=json.dumps(i['attributes']['stats']['items']),
                    tier=i['attributes']['stats']['skillTier'],
                    won=i['attributes']['stats']['winner'],
                    player_id=i['relationships']['player']['data']['id'],
                    match_id=ro2m[pa2r[i['id']]],
                    roster_id=pa2r[i['id']],
                )
                p.save()
        # Matches =(many-to-many)=> Players
        for m in matches:
            for r in m.roster_set.all():
                for pa in r.participant_set.all():
                    m.players.add(pa.player)
        return

    def _player_matches(self, reg, ign):
        url = f'https://api.dc01.gamelockerapp.com/shards/{reg}/matches'
        params = {
            'filter[playerNames]': [ign],
            'sort': '-createdAt',
        }
        res = self.request(url, params)

        # ================
        # Reshape the data
        # ================

        if res.get('errors', ''):
            result = res
        elif True:  # Debug
            with open('./tmp.json', 'w') as f:
                json.dump(res, f, indent=3)
        else:

            # matches is one time only
            _matches = {i['id']: [i['attributes']['duration'],
                                  i['attributes']['gameMode'],
                                  i['attributes']['patchVersion'],
                                  i['relationships']['rosters']['data']]
                        for i in res['data']}
            _rosters = {i['id']: [i['attributes']['stats']['heroKills'],
                                  i['attributes']['stats']['side'],
                                  i['attributes']['stats']['turretKills'],
                                  i['attributes']['stats']['turretsRemaining'],
                                  i['relationships']['participants']['data']]
                        for i in res['included'] if i['type'] == 'roster'}
            # participants is to be saved
            _participants = {i['id']: [i['attributes']['actor'],
                                       i['attributes']['shardId'],
                                       i['attributes']['stats']['kills'],
                                       i['attributes']['stats']['deaths'],
                                       i['attributes']['stats']['assists'],
                                       i['attributes']['stats']['gold'],
                                       i['attributes']['stats']['farm'],
                                       i['attributes']['stats']['items'],
                                       i['attributes']['stats']['skillTier'],
                                       i['attributes']['stats']['winner'],
                                       i['relationships']['player']['data']['id']]
                             for i in res['included'] if i['type'] == 'participant'}
            players = {
                i['id']: {
                    'name':     i['attributes']['name'],
                    'shard':    i['attributes']['shardId'],
                    'guild':    i['attributes']['stats']['guildTag'],
                    'elo':      i['attributes']['stats']['rankPoints']['ranked'],
                    'tier':     i['attributes']['stats']['skillTier'],
                    'wins':     i['attributes']['stats']['wins'],
                }
                for i in res['included'] if i['type'] == 'player'}
            participants = {k: {'actor': v[0],
                                'shard': v[1],
                                'kills': v[2],
                                'deaths': v[3],
                                'assists': v[4],
                                # KDA
                                'kda': (v[2] + v[4]) / (v[3] + 1),
                                'gold': int(v[5]),
                                'farm': int(v[6]),
                                'items': v[7][::-1][:6][::-1],
                                'tier': v[8],
                                'won': v[9],
                                'player_id': v[10]}
                            for k, v in _participants.items()}
            rosters = {k: {'team_kill_score': v[0],
                           'side': v[1].replace('/', '-'),
                           'turret_kill': v[2],
                           'turret_remain': v[3],
                           'participants': [participants[data['id']] for data in v[4]]}
                       for k, v in _rosters.items()}
            matches = [{'duration': v[0],
                        'mode': MODE_JA.get(v[1], v[1]),
                        'version': v[2],
                        'rosters': [rosters[r['id']] for r in v[3]],
                        }
                       for v in _matches.values()]
            result = {'matches': matches,
                      'players': players}
        return result

    def _request_without_region(self, ign, method):
        for r in SHARDS:
            res = method(r, ign)
            if res is not dict:
                break
            elif res.get('errors', ''):
                # もしエラーがあれば。
                continue
            else:
                break
        return res

    def single_player_without_region(self, ign):
        return self._request_without_region(ign, self.single_player)

    def matches_without_region(self, ign):
        return self._request_without_region(ign, self.matches)

    def player_matches_wo_region(self, ign):
        return self._request_without_region(ign, self.player_matches)


# ================
# Utilities
# ================
def itemname_to_cssreadable(name):
    return name.replace(' ', '-').replace("'", "").lower()


def particularplayer_from_singlematch(match, player_id):
    for r in match['rosters']:
        for p in r['participants']:
            if p['player_id'] == player_id:
                return p
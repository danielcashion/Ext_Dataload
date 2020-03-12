# # -*- coding: utf-8 -*-
from lxml import html
import requests
import re
from datetime import datetime
import json


class Keys:
    api_root = 'https://api.tourneymaster.org/v2/'
    response_content = 'response_content'

    #tourneymachine_events
    customer_id = 'IDCustomer'
    location_dictionary = 'location_dictionary'
    status = 'status'
    name = 'name'
    sport = 'sport'
    start_date = 'StartDate'
    end_date = 'EndDate'
    display_location = 'DisplayLocation'
    is_active_yn = 'is_active_YN'
    logo_url = 'logo_url'

    #tourneymachine_pools
    division_id = 'IDDivision'
    pool_description = 'pool_description'
    team_id = 'IDTeam'

    # tourneymachine_game_data
    tournament_id = 'IDTournament'
    game_id = 'IDGame'
    complex_id = 'IDComplex'
    tournament_endpoint = 'tournament_endpoint'
    tournament_name = 'tournament_name'
    tournament_division_id = 'tournament_division_id'
    tournament_division_name = 'tournament_division_name'
    time_period = 'time_period'
    location_id = 'location_id'
    location_name = 'location_name'
    last_update = 'last_update'
    game_date = 'game_date'
    game_time = 'game_time'
    away_team_id = 'away_team_id'
    away_team_name = 'away_team_name'
    home_team_id = 'home_team_id'
    home_team_name = 'home_team_name'
    away_score = 'away_score'
    home_score = 'home_score'

    # tourneymachine_locations
    locations_name = 'Name'
    address = 'Address'
    city = 'City'
    state = 'State'
    zip = 'Zip'
    long = 'Long'
    lat = 'Lat'
    notes = 'Notes'
    facility_id = 'IDFacilities'
    updated_by = 'updated_by'
    updated_datetime = 'updated_datetime'

    locations = 'locations'


keys = Keys()


#curr_date = datetime.utcnow()

_access_token = 'eyJraWQiOiIxU3lKYSsyRWZ5c3BvSWl1YkF5K0preTdEakNyMzRmT3I2NExsM1ZMZWJjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJhdWQiOiI0ZTZ1cThiNGYxZjRxNXFsOHFlMTBjcWZkYyIsImV2ZW50X2lkIjoiNmEwNmNhOWYtNzU2MS00MTFhLWFiNDMtNTRjYTlkMDZhNjYzIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1ODM5ODI2NzUsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0xX0tDRkNjeHNmNCIsImNvZ25pdG86dXNlcm5hbWUiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJleHAiOjE1ODM5ODYyNzUsImlhdCI6MTU4Mzk4MjY3NSwiZW1haWwiOiJhcGlfZGVtb0B0b3VybmV5bWFzdGVyLm9yZyJ9.gD0R8n_QNZV122b63Tid7GS7mIss0snzA19eL5cNvH1zF-htpwh54s2tK6_bpiONjjyHWYYhcxte-stp_43dKF2rUF4NHlc4Z09OfoNw0BDU_fdB1I0lR9BHh7rnMbD9sPSn8943Cah-ByPfwwenCwdVIqOXM2ForWuwoTR7dr0Gn-6VtSViz46wMd3Zqzd9_bTRnyUBp-Edo3J5FjwGN0I7HhSLR-o-qoSeMiMQm3Be0eGEttF7BteeMNEG-GTFKv2Xnm9g6MxhBBRxEsYE4By_38cEh6SvyWCGPWWwbjgdFP8NhLDmxzYHTaO5kw82VP9BcpkHbVlNJfZFsm2ALw'


def scrape(event, context):
    _tournament_id = event.get('tid')
    _tournament_base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'

    if not _tournament_id:
        raise KeyError('Missing tournament id (tid) command line arguement')

    _url = '{}={}'.format(_tournament_base_url, _tournament_id)
    response = requests.get(_url)
    get_tournament(response, **{keys.tournament_endpoint: _url, keys.tournament_id: _tournament_id})


def get_xpath_info(target, xpath_str):
    _ = target.xpath(xpath_str) or ''
    if isinstance(_, list):
        return _[0].strip()
    else:
        return _.strip()


def push_to_api(endpoint, payload):
    return requests.post(url="{}{}".format(keys.api_root, endpoint),
                         data=json.dumps(payload),
                         headers={'Content-Type': 'application/json',
                                  'Authorization': 'Bearer {}'.format(_access_token)})


def get_tournament(response, **kwargs):
    tournament_endpoint = kwargs.get(keys.tournament_endpoint)
    tournament_id = kwargs.get(keys.tournament_id)
    tree = html.fromstring(response.content)

    customer_id = tree.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]')[0].attrib.get('src').split('/')[4]
    divisions = tree.xpath('//div[@class="col-xs-6 col-sm-3"]')

    get_event(tree, tournament_id, customer_id)

    for division in divisions:
        try:
            last_update = division.xpath('./a/p/span/text()').extract()
            last_update = ''.join(last_update).replace('Last Updated', '').strip()
        except Exception as e:
            last_update = ''

        _url = 'https://admin.tourneymachine.com/Public/Results/{}'.format(division.xpath('./a/@href')[0])
        tournament_division_id = _url.split('IDDivision=')[-1]
        tournament_division_name = get_xpath_info(division, './a/div/text()')

        response = requests.get(_url)
        get_division_details(response, **{
            keys.tournament_endpoint: tournament_endpoint,
            keys.tournament_division_id: tournament_division_id,
            keys.tournament_id: tournament_id,
            keys.tournament_division_name: tournament_division_name,
            keys.customer_id: customer_id,
            keys.last_update: last_update
        })


def get_division_details(response, **kwargs):
    tree = html.fromstring(response.content)

    kwargs[keys.response_content] = response.content
    kwargs[keys.tournament_name] = get_xpath_info(tree, '//h1/a/text()')
    kwargs[keys.time_period] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentDates"]/text())')
    kwargs[keys.location_id] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentLocation"]/text())')

    locations = get_locations(tree, **kwargs)
    kwargs[keys.locations] = locations
    get_games(tree, **kwargs)
    get_pools(tree, **kwargs)


def get_event(response, tournament_id, customer_id):
    time_period = get_xpath_info(response, 'normalize-space(//div[@class="tournamentDates"]/text())')
    location = get_xpath_info(response, 'normalize-space(//div[@class="tournamentLocation"]/text())')

    try:
        sport = response.xpath('//div[@id="tournamentSport"]/div/text()')[1].strip()
    except Exception as e:
        sport = ''

    try:
        logo_url = response.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]')[0].attrib['src']
    except Exception as e:
        logo_url = ''

    try:
        start_date = time_period.split('-')[0].strip()
    except Exception as e:
        start_date = ''

    try:
        end_date = time_period.split('-')[1].strip()
    except Exception as e:
        end_date = ''

    # post event
    event_payload = {
        keys.tournament_id: tournament_id,
        keys.customer_id: customer_id,
        keys.location_dictionary: None,
        keys.status: None,
        keys.name: get_xpath_info(response, '//h1/a/text()'),
        keys.sport: sport,
        keys.start_date: start_date,
        keys.end_date: end_date,
        keys.display_location: location,
        keys.is_active_yn: 1,
        keys.logo_url: logo_url
    }
    r = push_to_api('ext_events', event_payload)


def get_games(response, **kwargs):
    games = response.xpath('//tr[following-sibling::tr and preceding-sibling::thead and count(child::*)>2]')

    if games:
        for game in games:
            game_id = get_xpath_info(game, './td[1]/text()')

            if not game_id:
                continue

            try:
                game_time = game.xpath('./td[2]//text()')[2].strip()
                if ':' not in game_time:
                    game_time = game.xpath('./td[2]/b/text()')[0].strip()
            except Exception as e:
                game_time = ''

            try:
                tmpt = game.xpath('./@class')[0].strip()
                tmp_away_team_id = re.findall(r'\steam_(\w+)', tmpt)
                try:
                    home_team_id = tmp_away_team_id[0]
                except IndexError:
                    home_team_id = ''
                try:
                    away_team_id = tmp_away_team_id[1]
                except IndexError:
                    away_team_id = ''
            except Exception as e:
                away_team_id = ''
                home_team_id = ''

            _location_name = get_xpath_info(game, 'normalize-space(./td[3]/text())').replace('\r', '')
            _game_payload = {
                keys.tournament_id: kwargs[keys.tournament_id],
                keys.game_id: game_id,
                keys.tournament_endpoint: kwargs[keys.tournament_endpoint],
                keys.tournament_name: kwargs[keys.tournament_name],
                keys.tournament_division_id: kwargs[keys.tournament_division_id],
                keys.tournament_division_name: kwargs[keys.tournament_division_name],
                keys.time_period: kwargs[keys.time_period],
                keys.location_id: kwargs[keys.location_id],
                keys.complex_id: kwargs[keys.locations][_location_name],
                keys.location_name: _location_name,
                keys.last_update: kwargs[keys.last_update],
                keys.game_date: get_xpath_info(game, 'normalize-space(./preceding-sibling::thead[1]/tr[1]/th/text())'),
                keys.game_time: game_time,
                keys.away_team_id: away_team_id,
                keys.away_team_name: get_xpath_info(game, './td[4]/text()'),
                keys.home_team_id: home_team_id,
                keys.home_team_name: get_xpath_info(game, './td[7]/text()'),
                keys.away_score: get_xpath_info(game, './td[5]/text()'),
                keys.home_score: get_xpath_info(game, './td[6]/text()'),
            }

            r = push_to_api('ext_games', _game_payload)


def get_pools(response, **kwargs):
    pools = response.xpath('//table[contains(@class, "table table-bordered table-striped tournamentResultsTable")]')

    for pool in pools:
        _pool_id = pool.xpath('.//thead/tr/th/text()')[0].strip()
        for team in pool.xpath('./tbody/tr/td/a/@href'):
            _pool_payload = {
                keys.tournament_id: kwargs[keys.tournament_id],
                keys.division_id: kwargs[keys.tournament_division_id],
                keys.pool_description: _pool_id,
                keys.team_id: team.split('IDTeam=')[1].strip()
            }
            r = push_to_api('ext_pools', _pool_payload)


def get_locations(response, **kwargs):
    _locations = {}

    address_info = response.xpath('//div[@class="panel panel-default panel-places complexList"]/div/div')

    _tmp = 0
    for i in range(0, int(len(address_info)/2)):
        _div_1 = address_info[i + _tmp]
        _div_2 = address_info[i + 1 + _tmp]
        _tmp += 1

        _id = _div_1.attrib['data-id']
        _name = _div_1.xpath('h4')[0].text
        _lat = re.search(r"complex{}.lat = \\'(.+?)\\';".format(i), str(kwargs['response_content'])).groups()[0]
        _long = re.search(r"complex{}.long = \\'(.+?)\\';".format(i), str(kwargs['response_content'])).groups()[0]

        try:
            _address = '{} {}'.format(_div_2.xpath('./a/address')[0].text.strip(),
                                  _div_2.xpath('./a/address/br')[0].tail.strip())
        except Exception as e:
            _address = ''
        _facilities = _div_2.xpath('./ul/li/b')
        _location_payload = {
            keys.location_dictionary: _id,
            keys.complex_id: _id,
            keys.tournament_id: kwargs[keys.tournament_id],
            keys.locations_name: _name,
            keys.address: _address,
            keys.long: _long,
            keys.lat: _lat,
            keys.notes: '',
            keys.is_active_yn: 1,
        }

        if _facilities:
            for facility in _facilities:
                _facility_id = facility.text
                _locations['{} - {}'.format(_name, _facility_id)] = _id
                _location_payload[keys.facility_id] = _facility_id,

                r = push_to_api('ext_locations', _location_payload)
        else:
            _locations[_name] = _id
            r = push_to_api('ext_locations', _location_payload)

    return _locations


scrape({'tid': 'h20190705131052863fcdd6f2ef3c542'}, None)
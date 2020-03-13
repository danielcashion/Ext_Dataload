# # -*- coding: utf-8 -*-
import time
import os

from lxml import html
import requests
import re
import json

from requests import HTTPError


class Keys:
    api_root = 'https://api.tourneymaster.org/v2/'
    response_content = 'response_content'
    method = 'method'
    key = 'key'
    row_num = 'row_num'


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
    long = 'tourneymachine_locations.Long'
    lat = 'Lat'
    notes = 'Notes'
    facility_id = 'IDFacilities'
    updated_by = 'updated_by'
    updated_datetime = 'updated_datetime'

    locations = 'locations'

class APIError(Exception):
    pass

class ScrapeError(Exception):
    pass

keys = Keys()


#curr_date = datetime.utcnow()

_access_token = 'eyJraWQiOiIxU3lKYSsyRWZ5c3BvSWl1YkF5K0preTdEakNyMzRmT3I2NExsM1ZMZWJjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJhdWQiOiI0ZTZ1cThiNGYxZjRxNXFsOHFlMTBjcWZkYyIsImV2ZW50X2lkIjoiNDA5MmNiNjctZTk2My00YmU2LWI4NTctN2JjMzE3ZGVlZDg4IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1ODQwNjI2OTIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0xX0tDRkNjeHNmNCIsImNvZ25pdG86dXNlcm5hbWUiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJleHAiOjE1ODQwNjYyOTIsImlhdCI6MTU4NDA2MjY5MiwiZW1haWwiOiJhcGlfZGVtb0B0b3VybmV5bWFzdGVyLm9yZyJ9.VNBwHHjcYHu4yeFtEAB0UYZAQ5aJw7FZwfUUX4izQ2-uYWFxbuyKCWYyPr7djGjy9syD0adxhCctMvu4qukepHfon440UYMnhRJZxw9a9_0V63jpk1bTsKI2RQzHVm_rk1IMbf-VuovN5AWD2ZR1ugLJZqHJQrfQ0uCGE81nRQIPOUwcdzEBYZqk2t6GnqZckSuoLfe4QMBx_d3cRWGHdKiT3j8gsrOGUcVGn6mztGge2IuzDNUXDW5_RRgwLv_Na5tmyXoqmRFrl3RHQZgt4QWG2uj7HRSbD96OFMEB6Wc9b8qrX1Uhgmnw26LEVGPbcaX8TquYGJekB4V9NL31pw'
_job_id = ''

_games = []
_pools = []


def scrape(event, context):
    _start = time.time()
    # Get access token if available
    if 'token' in event.keys():
        print('Using token from event["token"]: ', event['token'])
        global _access_token
        _access_token = event['token']
        global _job_id
        _job_id = event['job_id']

    _tournament_id = event.get('tid')
    _tournament_base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'

    if not _tournament_id:
        raise KeyError('Missing tournament id (tid) command line arguement')

    _url = '{}={}'.format(_tournament_base_url, _tournament_id)
    response = requests.get(_url)
    _event, _divisions, _locations = get_tournament(response, **{keys.tournament_endpoint: _url,
                                                              keys.tournament_id: _tournament_id})

    _end = time.time()
    _t_delta = _end - _start
    _message = 'Scraped {} games, {} pools, and {} locations across {} divisions for tournament {} ({}) in {} seconds'.format(
        len(_games), len(_pools), len(_locations), len(_divisions), _event[keys.name], _event[keys.tournament_id], _t_delta)

    print(_message)
    return {
        'message': _message
    }


def get_xpath_info(target, xpath_str):
    _ = target.xpath(xpath_str) or ''
    if isinstance(_, list):
        return _[0].strip()
    else:
        return _.strip()


def get_from_api(endpoint, payload, search_params):
    try:

        response = requests.get(url="{}{}?{}".format(keys.api_root, endpoint, search_params),
                                data=json.dumps(payload),
                                headers={'Content-Type': 'application/json',
                                         'Authorization': 'Bearer {}'.format(_access_token)})

        response.raise_for_status()

    except HTTPError as http_err:
        raise APIError(f'HTTP error occurred: {http_err}')
    except Exception as err:
        raise ScrapeError(f'Other error occurred: {err}')
    else:
        return response


def push_to_api(endpoint, payload, method='POST', **kwargs):
    try:
        if method == 'POST':
            response = requests.post(url="{}{}".format(keys.api_root, endpoint),
                             data=json.dumps(payload),
                             headers={'Content-Type': 'application/json',
                                      'Authorization': 'Bearer {}'.format(_access_token)})
        else:
            response = requests.put(url="{}{}?row_num={}".format(keys.api_root, endpoint, kwargs[keys.key]),
                                    data=json.dumps(payload),
                                    headers={'Content-Type': 'application/json',
                                             'Authorization': 'Bearer {}'.format(_access_token)})
        response.raise_for_status()

    except HTTPError as http_err:
        raise APIError(f'HTTP error occurred: {http_err}')
    except Exception as err:
        raise ScrapeError(f'Other error occurred: {err}')
    else:
        return response


def get_tournament(response, **kwargs):
    tournament_endpoint = kwargs.get(keys.tournament_endpoint)
    tournament_id = kwargs.get(keys.tournament_id)
    tree = html.fromstring(response.content)

    customer_id = tree.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]')[0].attrib.get('src').split('/')[4]
    divisions = tree.xpath('//div[@class="col-xs-6 col-sm-3"]')

    _cur_event = json.loads(get_from_api('ext_events', {}, '{}={}'.format(keys.tournament_id, tournament_id)).content)

    if _cur_event:
        _method = 'PUT'
        _event = get_event(tree, tournament_id, customer_id, 'PUT', **{keys.key: _cur_event[0][keys.row_num]})

    else:
        _method = 'POST'
        _event = get_event(tree, tournament_id, customer_id, _method)

    _locations = get_locations(html.fromstring(response.content), **{
            keys.tournament_endpoint: tournament_endpoint,
            keys.tournament_id: tournament_id,
            keys.customer_id: customer_id,
            keys.response_content: response.content,
            keys.method: _method
    })

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
            keys.last_update: last_update,
            keys.response_content: response.content,
            keys.locations: _locations,
            keys.method: _method
        })

    return _event, divisions, _locations


def get_division_details(response, **kwargs):
    status = 'Extracting division {}'.format(kwargs[keys.tournament_division_name])
    print(status)
    
    # Reporting progress to "system_jobs" table
    # The following line should be a call to "push_to_api" but apparently it does not support arbitrary primary key
    # Hence duplication
    
    requests.put(url="{}{}?job_id={}".format(keys.api_root, 'system_jobs', _job_id),
                data=json.dumps({'job_id': _job_id, 'status': status}),
                headers={'Content-Type': 'application/json',
                        'Authorization': 'Bearer {}'.format(_access_token)})

    tree = html.fromstring(response.content)

    kwargs[keys.response_content] = response.content
    kwargs[keys.tournament_name] = get_xpath_info(tree, '//h1/a/text()')
    kwargs[keys.time_period] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentDates"]/text())')
    kwargs[keys.location_id] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentLocation"]/text())')

    get_games(tree, **kwargs)
    get_pools(tree, **kwargs)

    return _games, _pools


def get_event(response, tournament_id, customer_id, method, **kwargs):
    print('Extracting {} event'.format(tournament_id))
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
    push_to_api('ext_events', event_payload, method, **kwargs)
    return event_payload


def get_games(response, **kwargs):
    games = response.xpath('//tr[following-sibling::tr and preceding-sibling::thead and count(child::*)>2]')
    _current_games = {}

    if kwargs[keys.method] == 'PUT':
        _current_games = get_from_api('ext_games', {}, '{}={}'.format(keys.tournament_id, kwargs[keys.tournament_id]))
        _current_games = json.loads(_current_games.content)
        _current_games = dict(((_[keys.tournament_id], _[keys.tournament_division_id], _[keys.game_id]), _[keys.row_num]) for _ in _current_games)

    if games:
        for game in games:
            game_id = get_xpath_info(game, './td[1]/text()')
            print('Extracting {} game'.format(game_id))
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
            _key = _current_games.get((_game_payload[keys.tournament_id],
                                       _game_payload[keys.tournament_division_id],
                                       _game_payload[keys.game_id]))

            push_to_api('ext_games', _game_payload, kwargs[keys.method] if _key else 'POST', **{keys.key: _key})
            _games.append(_game_payload)


def get_pools(response, **kwargs):
    pools = response.xpath('//table[contains(@class, "table table-bordered table-striped tournamentResultsTable")]')
    _current_pools = {}

    if kwargs[keys.method] == 'PUT':
        _current_pools = get_from_api('ext_pools', {}, '{}={}'.format(keys.tournament_id, kwargs[keys.tournament_id]))
        _current_pools = json.loads(_current_pools.content)
        _current_pools = dict(((_[keys.tournament_id], _[keys.division_id], _[keys.team_id], _[keys.pool_description]), _[keys.row_num]) for _ in _current_pools)

    for pool in pools:
        _pool_id = pool.xpath('.//thead/tr/th/text()')[0].strip()
        print('Extracting {} pool'.format(_pool_id))
        for team in pool.xpath('./tbody/tr/td/a/@href'):
            _pool_payload = {
                keys.tournament_id: kwargs[keys.tournament_id],
                keys.division_id: kwargs[keys.tournament_division_id],
                keys.pool_description: _pool_id,
                keys.team_id: team.split('IDTeam=')[1].strip()
            }
            _key = _current_pools.get((_pool_payload[keys.tournament_id],
                                      _pool_payload.get(keys.tournament_division_id),
                                      _pool_payload.get(keys.team_id),
                                      _pool_payload.get(keys.pool_description)))
            push_to_api('ext_pools', _pool_payload, kwargs[keys.method] if _key else 'POST', **{keys.key: _key})
            _pools.append(_pool_payload)


def get_locations(response, **kwargs):
    _locations = {}
    _curr_locations = {}

    if kwargs[keys.method] == 'PUT':
        _curr_locations = get_from_api('ext_locations', {}, '{}={}'.format(keys.tournament_id, kwargs[keys.tournament_id]))
        _curr_locations = json.loads(_curr_locations.content)
        _curr_locations = dict(((_[keys.tournament_id],_[keys.complex_id], _[keys.facility_id]), _[keys.row_num]) for _ in _curr_locations)

    address_info = response.xpath('//div[@class="panel panel-default panel-places complexList"]/div/div')

    _tmp = 0

    for i in range(0, int(len(address_info)/2)):

        _div_1 = address_info[i + _tmp]
        _div_2 = address_info[i + 1 + _tmp]
        _tmp += 1

        _id = _div_1.attrib['data-id']
        _name = _div_1.xpath('h4')[0].text
        print('Extracting {} location'.format(_name))
        _lat = re.search(r"complex{}.lat = \\'(.+?)\\';".format(i), str(kwargs['response_content'])).groups()[0]
        _long = re.search(r"complex{}.long = \\'(.+?)\\';".format(i), str(kwargs['response_content'])).groups()[0]

        try:
            # this may need to be tweaked for new data. Assumes all addresses will have same format
            _address = _div_2.xpath('./a/address')[0].text.strip()
            _city_state_zip = _div_2.xpath('./a/address/br')[0].tail.split(',')
            _city = _city_state_zip[0].strip()
            _state, _zip = _city_state_zip[1].strip().split(' ')

        except Exception as e:
            _address, _city, _state, _zip = '', '', '', ''

        _facilities = _div_2.xpath('./ul/li/b')
        _location_payload = {
            keys.location_dictionary: _id,
            keys.complex_id: _id,
            keys.tournament_id: kwargs[keys.tournament_id],
            keys.locations_name: _name,
            keys.address: _address,
            keys.city: _city,
            keys.state: _state,
            keys.zip: _zip,
            keys.long: _long,
            keys.lat: _lat,
            keys.notes: '',
            keys.is_active_yn: 1,
        }

        if _facilities:
            for facility in _facilities:
                _facility_id = facility.text
                _locations['{} - {}'.format(_name, _facility_id)] = _id
                _location_payload[keys.facility_id] = _facility_id
                _key = _curr_locations.get((_location_payload[keys.tournament_id],
                                            _location_payload[keys.complex_id],
                                            _location_payload[keys.facility_id]))

                r = push_to_api('ext_locations', _location_payload, kwargs[keys.method] if _key else 'POST',
                                **{keys.key: _key})
        else:
            _locations[_name] = _id
            _key = _curr_locations.get((_location_payload[keys.tournament_id],_location_payload[keys.complex_id], None))
            r = push_to_api('ext_locations', _location_payload, kwargs[keys.method] if _key else 'POST',
                            **{keys.key: _key})

    return _locations

# Do not run scrape if in Lambda
if 'LAMBDA_TASK_ROOT' not in os.environ:
    scrape({'tid': 'h20190705131052863fcdd6f2ef3c542'}, None)

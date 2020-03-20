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
    base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'
    response_content = 'response_content'
    method = 'method'
    key = 'key'
    row_num = 'row_num'
    pools = 'pools'
    games = 'games'
    job_id = 'job_id'
    access_token = 'token'
    token = 'token'
    tid = 'tid'
    message = 'message'
    POST = 'POST'
    PUT = 'PUT'
    insert_id = 'insertId'
    start_time = 'start_time'
    step_comments = 'step_comments'
    job_detail_id = 'job_detail_id'
    current_step = 'current_step'

    system_jobs = 'system_jobs'
    is_complete = 'is_complete_YN'

    system_jobs_details = 'system_jobs_details'
    step_description = 'step_description'
    step_id = 'step_id'


    #tourneymachine_events
    customer_id = 'IDCustomer'
    events_tablename = 'ext_events'
    location_dictionary = 'location_dictionary'
    status = 'status'
    name = 'name'
    sport = 'sport'
    start_date = 'StartDate'
    end_date = 'EndDate'
    display_location = 'DisplayLocation'
    is_active_yn = 'is_active_YN'
    logo_url = 'logo_url'
    debug = 'debug'


    #tourneymachine_pools
    pools_tablename = 'ext_pools'
    division_id = 'IDDivision'
    pool_description = 'pool_description'
    team_id = 'IDTeam'

    # tourneymachine_game_data
    tournament_id = 'IDTournament'
    game_id = 'IDGame'
    games_tablename = 'ext_games'
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
    locations_tablename = 'ext_locations'
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


step_descriptions = {
    1: 'Loading event info',
    2: 'Loading locations',
    3: 'Loading division ',
    4: 'Loading games | division ',
    5: 'Loading pools | division ',
}


class APIError(Exception):
    pass


class ScrapeError(Exception):
    pass


keys = Keys()

_games = []
_pools = []


def _start_step(description_details='', **kwargs):
    kwargs[keys.start_time] = time.time()
    _payload = {
        keys.job_id: kwargs.get(keys.job_id),
        keys.step_description: step_descriptions[kwargs.get(keys.current_step)] + description_details,
        keys.step_id: kwargs.get(keys.current_step),
        keys.is_active_yn: 1,
    }
    kwargs[keys.step_id] = push_to_api(keys.system_jobs_details, _payload, **kwargs).json()[keys.insert_id]

    return kwargs


def _finish_step(**kwargs):
    _end = time.time()
    _job_details_payload = {
        keys.job_id: kwargs.get(keys.job_id),
        keys.is_active_yn: 0,
        keys.step_comments: 'Completed in {0:.2f} seconds'.format(_end - kwargs.get(keys.start_time))
    }
    push_to_api(keys.system_jobs_details, _job_details_payload, f'?{keys.job_detail_id}={kwargs.get(keys.step_id)}',
                **kwargs)


def scrape(event, context):
    _start = time.time()
    _debug = event.get(keys.debug)
    _tournament_id = event.get(keys.tid)

    if not _tournament_id:
        raise KeyError('Missing tournament id (tid) command line arguement')

    _url = '{}={}'.format(keys.base_url, _tournament_id)
    _params = {
        keys.tournament_endpoint: _url,
        keys.tournament_id: _tournament_id,
        keys.job_id: event.get(keys.job_id),
        keys.access_token: event.get(keys.access_token),
        keys.debug: _debug
    }

    _payload = {keys.job_id: _params.get(keys.job_id), keys.status: 'Running'}
    push_to_api(keys.system_jobs, _payload, f'?{keys.job_id}={_params.get(keys.job_id)}', **_params)

    response = requests.get(_url)
    try:
        _event, _divisions, _locations = get_tournament(response, **_params)
    except ScrapeError as e:
        print(e)
        return

    _end = time.time()
    _t_delta = _end - _start
    _message = 'Scraped {} games, {} pools, and {} locations across {} divisions for tournament {} ({}) in {} seconds'.format(
        len(_games), len(_pools), len(_locations), len(_divisions), _event[keys.name], _event[keys.tournament_id], _t_delta)

    _payload = {
        keys.job_id: _params.get(keys.job_id),
        keys.status: _message,
        keys.is_active_yn: 0,
        keys.is_complete: 1,
    }
    push_to_api(keys.system_jobs, _payload, f'?{keys.job_id}={_params.get(keys.job_id)}', **_params)

    if _debug:
        print(_message)

    return {keys.message: _message}


def _valid_tournament(response, **kwargs):
    if re.search('com/Error', response.url):
        _payload = {
            keys.job_id: kwargs.get(keys.job_id),
            keys.status: 'Error: Invalid tournament ID',
            keys.is_active_yn: False,
            keys.is_complete: False,
        }

        push_to_api(keys.system_jobs, _payload, f'?{keys.job_id}={kwargs.get(keys.job_id)}', **kwargs)
        return False

    return True


def get_xpath_info(target, xpath_str):
    _ = target.xpath(xpath_str) or ''
    if isinstance(_, list):
        return _[0].strip()
    else:
        return _.strip()


def _get_header(token):
    return {'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'}


def get_from_api(endpoint, payload, search_params, **kwargs):
    try:
        response = requests.get(url=f"{keys.api_root}{endpoint}?{search_params}",
                                data=json.dumps(payload),
                                headers=_get_header(kwargs.get(keys.access_token)))

        response.raise_for_status()

    except HTTPError as http_err:
        raise APIError(f'HTTP error occurred: {http_err}')
    except Exception as err:
        raise ScrapeError(f'Other error occurred: {err}')
    else:
        return response


def push_to_api(endpoint, payload, params='', **kwargs):
    try:
        _func = requests.post if not params else requests.put
        response = _func(url=f"{keys.api_root}{endpoint}{params}",
                         data=json.dumps(payload),
                         headers=_get_header(kwargs.get(keys.access_token)))

        if kwargs.get(keys.debug):
            print(response.json())

        response.raise_for_status()

    except HTTPError as http_err:
        raise APIError(f'HTTP error occurred: {http_err}')
    except Exception as err:
        raise ScrapeError(f'Other error occurred: {err}')
    else:
        return response


def get_tournament(response, **kwargs):
    tournament_id = kwargs.get(keys.tournament_id)
    tree = html.fromstring(response.content)
    if not _valid_tournament(response, **kwargs):
        raise ScrapeError(f"Bad {keys.tournament_id}")

    customer_id = tree.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]')[0].attrib.get('src').split('/')[4]
    divisions = tree.xpath('//div[@class="col-xs-6 col-sm-3"]')

    _cur_event = json.loads(get_from_api('ext_events', {}, '{}={}'.format(keys.tournament_id, tournament_id), **kwargs).content)
    _current_pools, _current_games = {}, {}

    kwargs[keys.customer_id] = customer_id
    kwargs[keys.response_content] = response.content

    if _cur_event:
        kwargs[keys.method] = keys.PUT
        kwargs[keys.key] = _cur_event[0][keys.row_num]
    else:
        kwargs[keys.method] = keys.POST

    _event = get_event(tree, **kwargs)

    kwargs[keys.locations] = get_locations(html.fromstring(response.content), **kwargs)

    if kwargs[keys.method] == keys.PUT:
        _search_params = f'{keys.tournament_id}={kwargs[keys.tournament_id]}'
        _current_pools = get_from_api(keys.pools_tablename, {}, _search_params, **kwargs)
        _current_pools = json.loads(_current_pools.content)
        _current_pools = dict(((_[keys.tournament_id], _[keys.division_id], _[keys.team_id], _[keys.pool_description]),
                               _[keys.row_num]) for _ in _current_pools)
        _current_games = get_from_api(keys.games_tablename, {}, _search_params, **kwargs)
        _current_games = json.loads(_current_games.content)
        _current_games = dict(
            ((_[keys.tournament_id], _[keys.tournament_division_id], _[keys.game_id]), _[keys.row_num]) for _ in
            _current_games)

    for division in divisions:
        try:
            last_update = division.xpath('./a/p/span/text()').extract()
            last_update = ''.join(last_update).replace('Last Updated', '').strip()
        except Exception as e:
            last_update = ''

        _url = 'https://admin.tourneymachine.com/Public/Results/{}'.format(division.xpath('./a/@href')[0])

        response = requests.get(_url)
        kwargs[keys.tournament_division_id] = _url.split('IDDivision=')[-1]
        kwargs[keys.tournament_division_name] = get_xpath_info(division, './a/div/text()')
        kwargs[keys.last_update] = last_update
        kwargs[keys.response_content] = response.content
        kwargs[keys.pools] = _current_pools
        kwargs[keys.games] = _current_games

        get_division_details(response, **kwargs)

    return _event, divisions, kwargs[keys.locations]


def get_division_details(response, **kwargs):
    kwargs[keys.current_step] = 3
    kwargs[keys.start_time] = time.time()
    kwargs = _start_step(kwargs[keys.tournament_division_name], **kwargs)

    status = 'Extracting division {}'.format(kwargs[keys.tournament_division_name])
    if kwargs.get(keys.debug):
        print(status)

    _payload = {keys.job_id: kwargs.get(keys.job_id), keys.status: status}
    push_to_api(keys.system_jobs, _payload, f'?{keys.job_id}={kwargs.get(keys.job_id)}', **kwargs)

    tree = html.fromstring(response.content)

    kwargs[keys.response_content] = response.content
    kwargs[keys.tournament_name] = get_xpath_info(tree, '//h1/a/text()')
    kwargs[keys.time_period] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentDates"]/text())')
    kwargs[keys.location_id] = get_xpath_info(tree, 'normalize-space(//div[@class="tournamentLocation"]/text())')

    get_games(tree, **kwargs)
    get_pools(tree, **kwargs)
    _finish_step(**kwargs)

    return _games, _pools


def get_event(response, **kwargs):
    kwargs[keys.current_step] = 1
    kwargs[keys.start_time] = time.time()
    kwargs = _start_step(**kwargs)

    if kwargs.get(keys.debug):
        print('Extracting {} event'.format(kwargs.get(keys.tournament_id)))

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
        keys.tournament_id: kwargs.get(keys.tournament_id),
        keys.customer_id: kwargs.get(keys.customer_id),
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

    push_to_api(keys.events_tablename, event_payload, **kwargs)
    _finish_step(**kwargs)

    return event_payload


def get_games(response, **kwargs):
    kwargs[keys.current_step] = 4
    kwargs[keys.start_time] = time.time()
    kwargs = _start_step(kwargs[keys.tournament_division_name], **kwargs)

    games = response.xpath('//tr[following-sibling::tr and preceding-sibling::thead and count(child::*)>2]')
    _current_games = kwargs.get(keys.games)

    if games:
        for game in games:
            game_id = get_xpath_info(game, './td[1]/text()')
            if kwargs.get(keys.debug):
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

            push_to_api(keys.games_tablename, _game_payload, f'?row_num={_key}' if _key else '', **kwargs)
            _games.append(_game_payload)
    _finish_step(**kwargs)


def get_pools(response, **kwargs):
    kwargs[keys.current_step] = 5
    kwargs[keys.start_time] = time.time()
    kwargs = _start_step(kwargs[keys.tournament_division_name], **kwargs)

    pools = response.xpath('//table[contains(@class, "table table-bordered table-striped tournamentResultsTable")]')
    _current_pools = kwargs.get(keys.pools)

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
            push_to_api(keys.pools_tablename, _pool_payload, f'?row_num={kwargs[keys.key]}' if _key else '', **kwargs)
            _pools.append(_pool_payload)

    _finish_step(**kwargs)


def get_locations(response, **kwargs):
    kwargs[keys.current_step] = 2
    kwargs[keys.start_time] = time.time()
    kwargs = _start_step(**kwargs)

    _locations = {}
    _curr_locations = {}


    if kwargs[keys.method] == keys.PUT:
        _curr_locations = get_from_api('ext_locations', {}, '{}={}'.format(keys.tournament_id, kwargs[keys.tournament_id]), **kwargs)
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
        if kwargs.get(keys.debug):
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
                push_to_api(keys.locations_tablename, _location_payload, f'?row_num={kwargs[keys.key]}' if _key else '', **kwargs)
        else:
            _locations[_name] = _id
            _key = _curr_locations.get((_location_payload[keys.tournament_id],_location_payload[keys.complex_id], None))
            push_to_api(keys.locations_tablename, _location_payload,  f'?row_num={kwargs[keys.key]}' if _key else '', **kwargs)

    _finish_step(**kwargs)
    return _locations


# Do not run scrape if in Lambda
if 'LAMBDA_TASK_ROOT' not in os.environ:
    scrape({keys.tid: 'h20190705131052863fcdd6f2ef3c542',
            keys.debug: True,
            keys.job_id: '12334567823',
            keys.access_token: 'eyJraWQiOiIxU3lKYSsyRWZ5c3BvSWl1YkF5K0preTdEakNyMzRmT3I2NExsM1ZMZWJjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJhdWQiOiI0ZTZ1cThiNGYxZjRxNXFsOHFlMTBjcWZkYyIsImV2ZW50X2lkIjoiZWY4M2JiMzgtOGNlZi00Y2YyLWExN2QtYjdhMjMyMDA1Mjg0IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1ODQ2NTM0NjUsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0xX0tDRkNjeHNmNCIsImNvZ25pdG86dXNlcm5hbWUiOiJkYThiM2E5NS03ZjA4LTQzYjEtYmVkMS03MzM5OTczYjhiZWIiLCJleHAiOjE1ODQ2NTcwNjUsImlhdCI6MTU4NDY1MzQ2NSwiZW1haWwiOiJhcGlfZGVtb0B0b3VybmV5bWFzdGVyLm9yZyJ9.qwd8XO8pcOtci-P1aDSQXRdvYHwxQ9hVUJ12fNSD10ThjX5_OCHEL61x4ViJHwNGjZzcteZmIsN_iWmFwPgcT-RHC7SjDWID3cMYQkkhJ5B-kdh1T_uodKUR5a1LX4VieZxoNwU2fBosteTfXeG6FoThWdJbTQh-VK2lPCRcbGyB_0S2-9RBoEGqV_Cd0wdlSHWHv8b1l0jHkK5BvigQ7EPhiZkgz0szZ-WyKre4p1Hkh-wGxMu3zyGiLdOf9_ftv4SRSODIx-zQzCmGPu91oX_3SzXFrSRp8XJpkeFsXAPVSD_ZY1TwBx_oH2HjsXwj3PjIo81bavP4zd67t2-fIw'},
           None)

# # -*- coding: utf-8 -*-
import requests
import scrapy
import re
from datetime import datetime
import json

class Keys:
    api_root = 'https://api.tourneymaster.org/v2/'

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
    pool_id = 'IDPool'
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


keys = Keys()

class TidExtractorSpider(scrapy.Spider):
    name = 'TidExtractor'
    tournament_base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'
    allowed_domains = ['tourneymachine.com']
    start_urls = ['https://tourneymachine.com/Home.aspx/']
    curr_date = datetime.utcnow()
    access_token = 'eyJraWQiOiIxU3lKYSsyRWZ5c3BvSWl1YkF5K0preTdEakNyMzRmT3I2NExsM1ZMZWJjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIyNjE1M2UwMS03OWU0LTRhMGEtYmYzZC0xMmIzOTU2Zjk1NjYiLCJhdWQiOiI0ZTZ1cThiNGYxZjRxNXFsOHFlMTBjcWZkYyIsImV2ZW50X2lkIjoiNjIxYTllOGItN2MwYi00NzQ4LWI4MjItY2NhZmNmMzJmMmRlIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1ODM5NjIyMDksImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0xX0tDRkNjeHNmNCIsImNvZ25pdG86dXNlcm5hbWUiOiIyNjE1M2UwMS03OWU0LTRhMGEtYmYzZC0xMmIzOTU2Zjk1NjYiLCJleHAiOjE1ODM5NjU4MDksImlhdCI6MTU4Mzk2MjIwOSwiZW1haWwiOiJkYW5pZWwuY2FzaGlvbi5ueWNAZ21haWwuY29tIn0.gL941dhWkdOoFk2EqfsMjnxVoy17TThV7D-neYw1oStb0YiOWP_d-xMPr94jnw6eMHGwbZWDw_lJs0hSTFXsPgJYxt7a68LH49t7EhwaVB8sq7M0LHQsgrhrylgUD3x0qEHUKE3EbQZIbkowreS9jy-jgO5ePAWdT8qWmSZVFhOUVeI-Lc3z58kojI9rKstS0iVvE7vYRgKpA-vZoubf-sGr-Kp7QAs21TRin67nxZt3TBemTEUIFDwr5mIN3BROHdf4UTOLzlq95wVeTJ7xGLz1Vw5nmnGLePgVG-wcHN51JdXdxX9OGh-1aYG5uoA7uCXRnQz21OMRlRHkKp59Jw'

    @staticmethod
    def get_xpath_info(target, xpath_str):
        return target.xpath(xpath_str).get(default='').strip()

    def push_to_api(self, endpoint, payload):
        return requests.post(url="{}{}".format(keys.api_root, endpoint),
                             data=json.dumps(payload),
                             headers={'Content-Type': 'application/json',
                                     'Authorization': 'Bearer {}'.format(self.access_token)})

    def parse(self, response):
        if not self.tid:
            raise KeyError('Missing tournament id (tid) command line arguement')

        _tournament_endpoint = '{}={}'.format(self.tournament_base_url, self.tid)

        yield scrapy.FormRequest(_tournament_endpoint,
                                 method='GET',
                                 callback=self.get_tournament,
                                 meta={keys.tournament_endpoint: _tournament_endpoint, keys.tournament_id: self.tid})

    def get_tournament(self, response):
        try:
            tournament_endpoint = response.meta[keys.tournament_endpoint]
            tournament_id = response.meta[keys.tournament_id]
            customer_id = response.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]').attrib.get('src').split('/')[4]
            divisions = response.xpath('//div[@class="col-xs-6 col-sm-3"]')

            self.get_event(response, tournament_id, customer_id)
            for division in divisions:
                try:
                    last_update = division.xpath('./a/p/span/text()').extract()
                    last_update = ''.join(last_update).replace('Last Updated', '').strip()
                except Exception as e:
                    last_update = ''

                temp_url = division.xpath('./a/@href').extract_first()
                tournament_division_id = temp_url.split('IDDivision=')[-1]
                url = 'https://admin.tourneymachine.com/Public/Results/' + temp_url
                tournament_division_name = self.get_xpath_info(division, './a/div/text()')

                yield scrapy.FormRequest(url, method='GET', callback=self.get_division_details, meta={
                    keys.tournament_endpoint: tournament_endpoint,
                    keys.tournament_division_id: tournament_division_id,
                    keys.tournament_id: tournament_id,
                    keys.tournament_division_name: tournament_division_name,
                    keys.customer_id: customer_id,
                    keys.last_update: last_update
                })

        except Exception as e:
            print(str(e))

    def get_division_details(self, response):
        _division_details = {
            keys.tournament_name: self.get_xpath_info(response, '//h1/a/text()'),
            keys.time_period: self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentDates"]/text())'),
            keys.location_id: self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentLocation"]/text())'),
        }

        self.get_games(response, _division_details)
        self.get_pools(response, _division_details)

    def get_event(self, response, tournament_id, customer_id):
        time_period = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentDates"]/text())')
        location = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentLocation"]/text())')

        try:
            sport = response.xpath('//div[@id="tournamentSport"]/div/text()')[1].get().replace('\r\n', '').strip()
        except Exception as e:
            sport = ''

        try:
            logo_url = response.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]').attrib['src']
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
        event_payload = json.dumps({
            keys.tournament_id: tournament_id,
            keys.customer_id: customer_id,
            keys.location_dictionary: None,
            keys.status: None,
            keys.name: self.get_xpath_info(response, '//h1/a/text()'),
            keys.sport: sport,
            keys.start_date: start_date,
            keys.end_date: end_date,
            keys.display_location: location,
            keys.is_active_yn: 1,
            keys.logo_url: logo_url
        })

        r = requests.post(url="https://api.tourneymaster.org/v2/ext_events", data=event_payload,
                          headers={'Content-Type': 'application/json',
                                   'Authorization': 'Bearer {}'.format(self.access_token)})

    def get_games(self, response, division_details):
        game = response.xpath('//tr[following-sibling::tr and preceding-sibling::thead and count(child::*)>2]')

        if game:
            for j in game:
                game_id = self.get_xpath_info(j, './td[1]/text()')
                if not game_id:
                    continue

                try:
                    game_time = j.xpath('./td[2]//text()').extract()[2].strip()
                    if ':' not in game_time:
                        game_time = j.xpath('./td[2]/b/text()').extract_first().strip()
                except Exception as e:
                    game_time = ''

                try:
                    tmpt = j.xpath('./@class').extract_first().strip()
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

                _game_payload = {
                    keys.tournament_id: response.meta[keys.tournament_id],
                    keys.game_id: game_id,
                    keys.tournament_endpoint: response.meta[keys.tournament_endpoint],
                    keys.tournament_name: division_details[keys.tournament_name],
                    keys.tournament_division_id: response.meta[keys.tournament_division_id],
                    keys.tournament_division_name: response.meta[keys.tournament_division_name],
                    keys.time_period: division_details[keys.time_period],
                    keys.location_id: division_details[keys.location_id],
                    keys.complex_id: '',
                    keys.location_name: self.get_xpath_info(j, 'normalize-space(./td[3]/text())').replace('\r', ''),
                    keys.last_update: response.meta[keys.last_update],
                    keys.game_date: self.get_xpath_info(j, 'normalize-space(./preceding-sibling::thead[1]/tr[1]/th/text())'),
                    keys.game_time: game_time,
                    keys.away_team_id: home_team_id,  # D Cashion round that these were reversed 2023 06 27. The simplest way to address it is just to switch them in the payload.
                    keys.away_team_name: self.get_xpath_info(j, './td[4]/text()'),
                    keys.home_team_id: away_team_id,  # D Cashion round that these were reversed 2023 06 27. The simplest way to address it is just to switch them in the payload.
                    keys.home_team_name: self.get_xpath_info(j, './td[7]/text()'),
                    keys.away_score: self.get_xpath_info(j, './td[5]/text()'),
                    keys.home_score: self.get_xpath_info(j, './td[6]/text()'),
                }

                r = self.push_to_api('ext_games', _game_payload)

    def get_pools(self, response, division_details):
        pools = response.xpath('//table[contains(@class, "table table-bordered table-striped tournamentResultsTable")]')

        for pool in pools:
            _pool_id = pool.xpath('.//thead/tr/th/text()').get().strip()
            for team in pool.xpath('./tbody/tr/td/a/@href').getall():
                _pool_payload = {
                    keys.tournament_id: response.meta[keys.tournament_id],
                    keys.division_id: response.meta[keys.tournament_division_id],
                    keys.pool_id: _pool_id,
                    keys.pool_description: _pool_id,
                    keys.team_id: team.split('IDTeam=')[1].strip()
                }
                r = self.push_to_api('ext_pools', _pool_payload)

    def get_locations(self, response, division_details):
        pass

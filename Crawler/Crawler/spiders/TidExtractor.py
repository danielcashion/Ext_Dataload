# # -*- coding: utf-8 -*-
import requests
import scrapy
import re
from datetime import datetime
from Crawler.items import TourneymachineItem
import json

class TidExtractorSpider(scrapy.Spider):
    name = 'TidExtractor'
    tournament_base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'
    allowed_domains = ['tourneymachine.com']
    start_urls = ['https://tourneymachine.com/Home.aspx/']
    curr_date = datetime.utcnow()
    access_token = 'eyJraWQiOiIxU3lKYSsyRWZ5c3BvSWl1YkF5K0preTdEakNyMzRmT3I2NExsM1ZMZWJjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIyNjE1M2UwMS03OWU0LTRhMGEtYmYzZC0xMmIzOTU2Zjk1NjYiLCJhdWQiOiI0ZTZ1cThiNGYxZjRxNXFsOHFlMTBjcWZkYyIsImV2ZW50X2lkIjoiNjIxYTllOGItN2MwYi00NzQ4LWI4MjItY2NhZmNmMzJmMmRlIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1ODM5NjIyMDksImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0xX0tDRkNjeHNmNCIsImNvZ25pdG86dXNlcm5hbWUiOiIyNjE1M2UwMS03OWU0LTRhMGEtYmYzZC0xMmIzOTU2Zjk1NjYiLCJleHAiOjE1ODM5NjU4MDksImlhdCI6MTU4Mzk2MjIwOSwiZW1haWwiOiJkYW5pZWwuY2FzaGlvbi5ueWNAZ21haWwuY29tIn0.gL941dhWkdOoFk2EqfsMjnxVoy17TThV7D-neYw1oStb0YiOWP_d-xMPr94jnw6eMHGwbZWDw_lJs0hSTFXsPgJYxt7a68LH49t7EhwaVB8sq7M0LHQsgrhrylgUD3x0qEHUKE3EbQZIbkowreS9jy-jgO5ePAWdT8qWmSZVFhOUVeI-Lc3z58kojI9rKstS0iVvE7vYRgKpA-vZoubf-sGr-Kp7QAs21TRin67nxZt3TBemTEUIFDwr5mIN3BROHdf4UTOLzlq95wVeTJ7xGLz1Vw5nmnGLePgVG-wcHN51JdXdxX9OGh-1aYG5uoA7uCXRnQz21OMRlRHkKp59Jw'

    def parse(self, response):
        if not self.tid:
            raise KeyError('Missing tournament id (tid) command line arguement')

        _tournament_endpoint = '{}={}'.format(self.tournament_base_url, self.tid)

        yield scrapy.FormRequest(_tournament_endpoint,
                                 method='GET',
                                 callback=self.get_tournament,
                                 meta={'tournament_endpoint': _tournament_endpoint, 'tournament_id': self.tid})

    def get_tournament(self, response):
        try:
            tournament_endpoint = response.meta['tournament_endpoint']
            tournament_id = response.meta['tournament_id']
            customer_id = response.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]').attrib.get('src').split('/')[4]
            divisions = response.xpath('//div[@class="col-xs-6 col-sm-3"]')
            time_period = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentDates"]/text())')
            location = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentLocation"]/text())')

            try:
                sport = response.xpath('//div[@id="tournamentSport"]/div/text()')[1].get().replace('\r\n',
                                                                                                   '').strip()
            except Exception as e:
                sport = ''

            try:
                logo_url = response.xpath('//img[@class="tournamentLogo img-thumbnail img-responsive"]').attrib[
                    'src']
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
                'IDTournament': tournament_id,
                'IDCustomer': customer_id,
                'location_dictionary': None,
                'status': None,
                'name': self.get_xpath_info(response, '//h1/a/text()'),
                'sport': sport,
                'StartDate': start_date,
                'EndDate': end_date,
                'DisplayLocation': location,
                'is_active_YN': 1,
                'logo_url': logo_url
            })

            r = requests.post(url="https://api.tourneymaster.org/v2/ext_events", data=event_payload,
                              headers={'Content-Type': 'application/json',
                                       'Authorization': 'Bearer {}'.format(self.access_token)})

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
                    'tournament_endpoint': tournament_endpoint,
                    'tournament_division_id': tournament_division_id,
                    'tournament_id': tournament_id,
                    'tournament_division_name': tournament_division_name,
                    'customer_id': customer_id,
                    'last_update': last_update
                })

        except Exception as e:
            print(str(e))

    @staticmethod
    def get_xpath_info(target, xpath_str):
        return target.xpath(xpath_str).get(default='').strip()

    def get_division_details(self, response):
        tournament_name = self.get_xpath_info(response, '//h1/a/text()')
        time_period = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentDates"]/text())')
        location = self.get_xpath_info(response, 'normalize-space(//div[@class="tournamentLocation"]/text())')
        game = response.xpath('//tr[following-sibling::tr and preceding-sibling::thead and count(child::*)>2]')

        if game:
            for j in game:
                item = TourneymachineItem()
                game_id = self.get_xpath_info(j, './td[1]/text()')
                if not game_id:
                    continue

                try:
                    game_time = j.xpath('./td[2]//text()').extract()[2].strip()
                    if ':' not in game_time:
                        game_time = j.xpath('./td[2]/b/text()').extract_first().strip()
                except Exception as e:.gitignore
                    game_time = ''

                try:
                    tmpt = j.xpath('./@class').extract_first().strip()
                    tmp_away_team_id = re.findall(r'\steam_(\w+)',tmpt)
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

                game_payload = {
                    'IDTournament': response.meta['tournament_id'],
                    'IDGame': game_id,
                    'tournament_endpoint': response.meta['tournament_endpoint'],
                    'tournament_name': tournament_name,
                    'tournament_division_id': response.meta['tournament_division_id'],
                    'tournament_division_name': response.meta['tournament_division_name'],
                    'time_period': time_period,
                    'location_id': location,
                    'IDComplex': '',
                    'location_name': self.get_xpath_info(j, 'normalize-space(./td[3]/text())').replace('\r', ''),
                    'last_update': response.meta['last_update'],
                    'game_date': self.get_xpath_info(j, 'normalize-space(./preceding-sibling::thead[1]/tr[1]/th/text())'),
                    'game_id': game_id,
                    'game_time': game_time,
                    'away_team_id': away_team_id,
                    'away_team_name': self.get_xpath_info(j, './td[4]/text()'),
                    'home_team_id': home_team_id,
                    'home_team_name': self.get_xpath_info(j, './td[7]/text()'),
                    'away_score': self.get_xpath_info(j, './td[5]/text()'),
                    'home_score': self.get_xpath_info(j, './td[6]/text()'),
                }

                r = requests.post(url="https://api.tourneymaster.org/v2/ext_games", data=json.dumps(game_payload),
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': 'Bearer {}'.format(self.access_token)})




# # -*- coding: utf-8 -*-
import requests
import scrapy
import re
from datetime import datetime
from Crawler.items import TourneymachineItem


class TidExtractorSpider(scrapy.Spider):
    name = 'TidExtractor'
    tournament_base_url = 'https://tourneymachine.com/Public/Results/Tournament.aspx?IDTournament'
    allowed_domains = ['tourneymachine.com']
    start_urls = ['https://tourneymachine.com/Home.aspx/']
    curr_date = datetime.utcnow()

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

            for division in divisions:
                temp_url = division.xpath('./a/@href').extract_first()
                tournament_division_id = temp_url.split('IDDivision=')[-1]
                url = 'https://admin.tourneymachine.com/Public/Results/' + temp_url
                tournament_division_name = self.get_xpath_info(division, './a/div/text()')

                try:
                    last_update = division.xpath('./a/p/span/text()').extract()
                    last_update = ''.join(last_update).replace('Last Updated', '').strip()
                except Exception as e:
                    last_update = ''

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
        event_payload = {
            'IDTournament': response.meta['tournament_id'],
            'IDCustomer': response.meta['customer_id'],
            'location_dictionary': response.meta['tournament_id'],
            'status': '',
            'name': tournament_name,
            'sport': sport,
            'StartDate': start_date,
            'EndDate': end_date,
            'DisplayLocation': location,
            'is_active_YN': 1,
            'created_by': 'scraper',
            'created_datetime': self.curr_date,
            'updated_by': None,
            'updated_datetime': None,
            'logo_url': logo_url
        }

        r = requests.post(url="https://api.tourneymaster.org/v2/ext_events", data=event_payload,
                          headers={'Authorization': 'access_token myToken'})

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
                except Exception as e:
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
                    'is_active' : 1,
                    'created_by': 'scraper',
                    'created_datetime': self.curr_date,
                    'updated_by': None,
                    'updated_datetime': None
                }

                r = requests.post(url="https://api.tourneymaster.org/v2/ext_games", data=game_payload,
                                  headers={'Authorization': 'access_token myToken'})




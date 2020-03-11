# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import requests

from Crawler.items import TourneymachineItem


class CrawlerPipeline(object):
    i = 0

    def process_item(self, item, spider):
        if isinstance(item, TourneymachineItem):
            try:
                # send to endpoint
                print('Sending {}'.format(str(self.i)))
                print(item)

                # try:
                #     start_date = item['time_period'].split('-')[0].strip()
                # except Exception as e:
                #     start_date = ''
                #
                # try:
                #     end_date = item['time_period'].split('-')[1].strip()
                # except Exception as e:
                #     end_date = ''
                #
                # event_payload = {
                #     'IDTournament': item['tournament_id'],
                #     'IDCustomer': item['customer_id'],
                #     'location_dictionary': item['tournament_id'],
                #     'status': '',
                #     'name': item['tournament_name'],
                #     'sport': item['sport'],
                #     'StartDate': start_date,
                #     'EndDate': end_date,
                #     'DisplayLocation': item['location'],
                #     'is_active_YN': 1,
                #     'created_by': 'scraper',
                #     'created_datetime': item['created_datetime'],
                #     'updated_by': None,
                #     'updated_datetime': None,
                #     'logo_url': item['logo_url']
                # }

                # r = requests.post(url=API_ENDPOINT, data=item)
                # response = r.text

                self.i += 1
            except Exception as e:
                print(str(e))
            return item

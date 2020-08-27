import json
import crawler


def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['body'])
    message['job_id'] = event['Records'][0]['messageId']
    print('Message: ', message, '\nEvent: ', event)

    res = crawler.scrape(message, None)

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': 'Result: ' + res['message'] + '\nEvent: ' + json.dumps(event)
    }

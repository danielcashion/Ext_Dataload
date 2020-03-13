import json
import boto3
import requests

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/564748484972/TMDataLoad'

system_jobs_url = "https://api.tourneymaster.org/v2/system_jobs"

def lambda_handler(event, context):
	print('Event: ', event)
	message = {
		'token': event['headers']['Authorization'].replace('Bearer ', ''),
		'tid': event['queryStringParameters']['tid'],
		'email': event['requestContext']['authorizer']['claims']['email'],
		'cognito:username': event['requestContext']['authorizer']['claims']['cognito:username']
	}
	res = add_job(message)
	# TODO implement
	message['job_id'] = res['MessageId']

	requests.post(url=system_jobs_url,
                data=json.dumps({'job_id': message['job_id'], 'status': 'Started'}),
                headers={'Content-Type': 'application/json',
                        				'Authorization': 'Bearer {}'.format(message['token'])})
	# try:
	# except requests.HTTPError as http_err:
	# 	print(f'HTTP error occurred: {http_err}')
	# except Exception as err:
	# 	print(f'Other error occurred: {err}')

	return {
		'isBase64Encoded': False,
		'statusCode': 200,
		'body': json.dumps({ 'success': 'true', 'message': message })
	}

def add_job(message):
	response = sqs.send_message(
			QueueUrl=queue_url,
			DelaySeconds=0,
			MessageBody=json.dumps(message)
	)

	print(response['MessageId'])
	return response
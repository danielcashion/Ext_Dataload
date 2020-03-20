import json
import boto3
import requests
import traceback

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/564748484972/TMDataLoad'
resHeaders = {'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
					'Access-Control-Allow-Methods': 'GET,POST,UPDATE,DELETE,OPTIONS',
					'Access-Control-Allow-Origin': '*'
}

system_jobs_url = "https://api.tourneymaster.org/v2/system_jobs"

def lambda_handler(event, context):
	try:
		print('Event: ', event)
		message = {
			'token': event['headers']['Authorization'].replace('Bearer ', ''),
			'tid': event['queryStringParameters']['tid'],
			'email': event['requestContext']['authorizer']['claims']['email'],
			'cognito:username': event['requestContext']['authorizer']['claims']['cognito:username']
		}
		res = add_job(message)
		message['job_id'] = res['MessageId']

		requests.post(url=system_jobs_url,
									data=json.dumps({'job_id': message['job_id'], 'status': 'Started'}),
									headers={'Content-Type': 'application/json',
														'Authorization':'Bearer {}'.format(message['token'])}					
									)
	except:
		print(f'Error: {traceback.format_exc()}')
		return {
			'isBase64Encoded': False,
			'statusCode': 404,
			'body': json.dumps({'success': 'false', 'message': traceback.format_exc()}),
			'headers': resHeaders
		}
	else:
		return {
			'isBase64Encoded': False,
			'statusCode': 200,
			'body': json.dumps({'success': 'true', 'message': message}),
			'headers': resHeaders
		}

def add_job(message):
	response = sqs.send_message(
			QueueUrl=queue_url,
			DelaySeconds=0,
			MessageBody=json.dumps(message)
	)

	print(response['MessageId'])
	return response
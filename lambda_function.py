import json
import boto3
import os
from botocore.exceptions import ClientError # type: ignore

# Initialize AWS client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Status check Lambda handler"""
    try:
        # Parse input data
        input_data = event
        if isinstance(event, str):
            input_data = json.loads(event)
            
        if 'body' in input_data:
            if isinstance(input_data['body'], str):
                input_data = json.loads(input_data['body'])
            else:
                input_data = input_data['body']
        
        print('Received status check request:', json.dumps(input_data))
        
        # Extract required parameters
        user_id = input_data.get('userId')
        device_id = input_data.get('deviceId')
        
        if not user_id or not device_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing userId or deviceId',
                    'status': 'ERROR'
                })
            }
            
        # Check if firmware exists in S3
        binary_s3_key = f'{user_id}/compiled-binaries/{device_id}/firmware.bin'
        
        try:
            # Check if file exists
            s3.head_object(
                Bucket=os.environ['FIRMWARE_BUCKET'],
                Key=binary_s3_key
            )
            
            # Generate signed URL for firmware download
            signed_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': os.environ['FIRMWARE_BUCKET'],
                    'Key': binary_s3_key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'COMPLETED',
                    'firmwareUrl': signed_url,
                    'deviceId': device_id,
                    'userId': user_id,
                    'message': 'Firmware compilation completed'
                })
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # File doesn't exist yet
                return {
                    'statusCode': 202,
                    'body': json.dumps({
                        'status': 'PROCESSING',
                        'deviceId': device_id,
                        'userId': user_id,
                        'message': 'Firmware compilation in progress'
                    })
                }
            else:
                # Some other error occurred
                raise
                
    except Exception as e:
        print(f'Error in status check: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'status': 'ERROR',
                'message': 'Failed to check compilation status'
            })
        }
import boto3

# AWS 설정
def create_rekognition_client():
    session = boto3.Session(
        aws_access_key_id='AKIAU6GDUY4XWGINNXO6',
        aws_secret_access_key='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',
        region_name='ap-northeast-2'
    )
    return session.client('rekognition')

rekognition_client = create_rekognition_client()
bucket_name = 'test-ju-upload'

# 이미지 비교 함수
def compare_faces(source_bytes,target_image):
    response = rekognition_client.compare_faces(
        SimilarityThreshold=80,
        SourceImage={'Bytes': source_bytes},
        TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': target_image}}
    )

    return len(response['FaceMatches'])



import boto3
import os
import json
import logging
from PIL import Image
import urllib.parse
import imghdr


s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

logging.getLogger().setLevel(logging.INFO)

def extract_file_id(object_key):
    file_name = object_key.split('/')[-1]
    file_id = file_name.split('.')[0]
    return file_id

def lambda_handler(event, context):
    # Define the target bucket for thumbnails
    target_bucket = 'test.target.image.processor.dev'

    # Define the sizes for thumbnails
    thumbnail_sizes = [120, 320, 1200]

    thumbnail_sizes_created = set()

    for record in event['Records']:
        # Get the source bucket and key from the S3 event
        source_bucket = record['s3']['bucket']['name']
        source_key = record['s3']['object']['key']
        source_key = urllib.parse.quote(source_key)

        logging.info("Processing the encoded source_key: "+ source_key + "from bucket: " + source_bucket)
        file_id = extract_file_id(source_key)
        logging.info("fileid is: " + file_id)
        image_path = '/tmp/' + file_id + '.jpg'
        s3_client.download_file(source_bucket, source_key, image_path)

        logging.info("Downloaded the image")

        width, height = downloaded_image_size(image_path)
        logging.info("Image width: %d, height: %d", width, height)

        # Create thumbnails for each size
        for size in thumbnail_sizes:
                    # Generate the thumbnail file name
            save_image_path = save_image(size,file_id)
            logging.info("saved in local path "+ save_image_path)

            if width > size and height > size:
                # Create the thumbnail
              thumbnail_width, thumbnail_height, thumbnail_content_type, thumbnail_memory_size = create_thumbnail(
                    image_path, save_image_path, source_key, target_bucket, size)
              thumbnail_sizes_created.add(size)

              send_sns_notification(file_id, thumbnail_width, thumbnail_height, size, thumbnail_memory_size,thumbnail_content_type)

        logging.info("created thumbnails")

        return {
             'statusCode': 200,
              'body': 'Thumbnails created and uploaded successfully'
        }

def send_sns_notification(file_id, width, height, size, memory_size, content_type):
    sns = boto3.client('sns', region_name = "eu-west-3")
    message = {
        'file_id': file_id,
        'width': width,
        'height': height,
        'size': size,
        'memory_size': memory_size,
        'content_type': content_type
    }

    response = sns.publish(
        TopicArn='arn:aws:sns:eu-west-3:251251521134:image-processor-sns-topic',
        Message=json.dumps(message)
    )

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logging.info('SNS notification sent successfully.')
    else:
        logging.error('Failed to send SNS notification.')


def downloaded_image_size(image_path):
    with Image.open(image_path) as img:
        return img.size



def create_folder_if_not_exists_for_local(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def save_image(size, file_id):
    folder_path = os.path.join('/tmp', str(size))
    create_folder_if_not_exists_for_local(folder_path)
    save_image_path = os.path.join(folder_path, file_id + '.jpg')
    return save_image_path

def create_folder_if_not_exists(bucket_name, folder_name):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=f"{folder_name}/")
    except:
        s3_client.put_object(Bucket=bucket_name, Key=f"{folder_name}/")

def get_thumbnail_path(source_key, size, target_bucket):
    folder_name = str(size)

    create_folder_if_not_exists(target_bucket, folder_name)

    return f"{folder_name}/{source_key}"

def create_thumbnail(image_path, save_image_path,  source_key, target_bucket, size):
    with Image.open(image_path) as image:
        image.thumbnail((size, size))
        thumbnail_path = get_thumbnail_path(source_key, size, target_bucket)
        image.save(save_image_path)
        logging.info("created paths to upload the image: "+thumbnail_path)
        upload_to_s3(save_image_path, target_bucket, thumbnail_path)
        logging.info("Image uploaded to " + thumbnail_path)

        thumbnail_width, thumbnail_height = image.size
        thumbnail_content_type = imghdr.what(None, h=open(save_image_path, 'rb').read())
        thumbnail_memory_size = os.stat(save_image_path).st_size

        return thumbnail_width, thumbnail_height, thumbnail_content_type, thumbnail_memory_size



def upload_to_s3(file_path, target_bucket_name, uploaded_key):
    logging.info("Image is uploading to file_path: " + file_path + ", target_bucket_name: " + target_bucket_name + ", upload_key" + uploaded_key)
    s3_client.upload_file(file_path, target_bucket_name, uploaded_key)


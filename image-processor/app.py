import boto3
import os
import logging
import tempfile
import json
from PIL import Image
import urllib.parse

s3_client = boto3.client('s3')
#sns_client = boto3.client('sns')

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
               create_thumbnail(image_path, save_image_path, source_key, target_bucket, size)
               thumbnail_sizes_created.add(size)
        logging.info("created thumbnails")
            # Send notification to SNS
        # sns_topic_arn = 'arn:aws:sns:eu-west-3:251251521134:image-processor-sns-topic'
        # message = {
        #     'file_id': file_id,
        #     'bucket': target_bucket,
        #     'sizes': list(thumbnail_sizes)  # Convert set to a list for JSON serialization
        #             }
        # sns_client.publish(
        #     TopicArn=sns_topic_arn,
        #     Message=json.dumps(message)
        # )

        return {
             'statusCode': 200,
              'body': 'Thumbnails created and uploaded successfully'
        }

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
        logging.info("Image uploaded to " + thumbnail_path )


def upload_to_s3(file_path, target_bucket_name, uploaded_key):
    logging.info("Image is uploading to file_path: " + file_path + ", target_bucket_name: " + target_bucket_name + ", upload_key" + uploaded_key)
    s3_client.upload_file(file_path, target_bucket_name, uploaded_key)


import os

import boto3


BUCKET_NAME = "jfrye-plant-flashcards-lzoqgn6e"
PHOTOS_ROOT_NAME = "PlantPhotos"
CACHE_LOCATION = "../plant_flashcards_cache"
CACHED_PHOTOS_ROOT = CACHE_LOCATION + "/" + PHOTOS_ROOT_NAME


def download_missing_photos(bucket, taxon):
    for obj in bucket.objects.filter(Prefix=PHOTOS_ROOT_NAME + "/" + "/".join(taxon)):
        local_file_path = CACHE_LOCATION + "/" + obj.key
        if os.path.isfile(local_file_path):
            continue

        # If the destination folders are missing, we must create them first
        local_file_folder = os.path.dirname(local_file_path)
        if not os.path.exists(local_file_folder):
            os.makedirs(local_file_folder)

        print("Downloading a missing photo!")
        with open(local_file_path, "wb") as f:
            bucket.download_fileobj(obj.key, f)


def ensure_photos_cached(taxon):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    download_missing_photos(bucket, taxon)

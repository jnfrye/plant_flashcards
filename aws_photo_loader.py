import os

import boto3

import constants as const


BUCKET_NAME = "jfrye-plant-flashcards-lzoqgn6e"
PHOTOS_ROOT_NAME = "PlantPhotos"


def get_photo_paths(taxon):
    _ensure_photos_cached(taxon)

    taxon_photos_path = PHOTOS_ROOT_NAME + "/" + "/".join(taxon)
    photo_files = os.listdir(const.CACHE_ROOT + "/" + taxon_photos_path)
    photo_paths = [taxon_photos_path + "/" + x for x in photo_files]

    return photo_paths


def _ensure_photos_cached(taxon):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    _download_missing_photos(bucket, taxon)


def _download_missing_photos(bucket, taxon):
    photos_bucket_path = PHOTOS_ROOT_NAME + "/" + "/".join(taxon)
    objects = list(bucket.objects.filter(Prefix=photos_bucket_path))
    if len(objects) == 0:
        raise Exception(f"No photos in bucket at '{photos_bucket_path}'!")

    for obj in objects:
        local_file_path = const.CACHE_ROOT + "/" + obj.key
        if os.path.isfile(local_file_path):
            continue

        # If the destination folders are missing, we must create them first
        local_file_folder = os.path.dirname(local_file_path)
        if not os.path.exists(local_file_folder):
            os.makedirs(local_file_folder)

        print("Downloading a missing photo!")
        with open(local_file_path, "wb") as f:
            bucket.download_fileobj(obj.key, f)

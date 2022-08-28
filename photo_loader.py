import os

import boto3


BUCKET_NAME = "jfrye-plant-flashcards-lzoqgn6e"
PHOTOS_ROOT_NAME = "PlantPhotos"
CACHE_LOCATION = "../plant_flashcards_cache"
CACHED_PHOTOS_ROOT = CACHE_LOCATION + "/" + PHOTOS_ROOT_NAME


def get_all_taxons():
    client = boto3.client('s3')
    paginator = client.get_paginator('list_objects')
    result = paginator.paginate(Bucket=BUCKET_NAME)

    # The result object is an iterator of dictionaries; the 'Contents' key contains the lists of S3 objects.
    # Each 'Contents' key can hold a maximum of 1000 entries, so we need to iterate over them as well.
    # Each entry in 'Contents' is itself a dictionary; the 'Key' key has the S3 object's full key.

    all_taxons = []
    for data in result:
        for item in data['Contents']:
            # Because the prefix delimiter is '/' we can use the 'dirname' function to extract the S3 prefix
            prefix = os.path.dirname(item['Key'])

            # The top-level prefix is always 'PlantPhotos', which we can discard
            taxon = tuple(x for x in prefix.split('/')[1:])
            all_taxons.append(taxon)

    return list(set(all_taxons))


def download_missing_photos(bucket, taxon):
    for obj in bucket.objects.filter(Prefix=PHOTOS_ROOT_NAME + "/" + "/".join(taxon)):
        local_file_path = CACHE_LOCATION + "/" + obj.key
        if os.path.isfile(local_file_path):
            continue

        # If the destination folders are missing, we must create them first
        local_file_folder = os.path.dirname(local_file_path)
        if not os.path.exists(local_file_folder):
            os.makedirs(local_file_folder)

        print("Downloading " + obj.key)
        with open(local_file_path, "wb") as f:
            bucket.download_fileobj(obj.key, f)


def ensure_photos_cached(taxon):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    download_missing_photos(bucket, taxon)


def main():
    get_all_taxons()


if __name__ == "__main__":
    main()

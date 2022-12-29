import os
import random

from google_images_search import GoogleImagesSearch

import constants as const

PHOTOS_ROOT_NAME = "GISPlantPhotos"
MAX_PHOTO_COUNT = 5


def get_photo_paths(taxon):
    gis = GoogleImagesSearch(const.CONFIG[const.GOOGLE_API_KEY], const.CONFIG[const.GOOGLE_SEARCH_ENGINE_CX])
    search_params = {
        'q': f'"{taxon[1]} {taxon[2]}"',
        'num': 20,
        'fileType': 'jpg',
        'rights': 'cc_publicdomain|cc_attribute|cc_sharealike|cc_noncommercial|cc_nonderived',
        'imgType': 'photo',
        'imgSize': 'large'
    }

    taxon_photos_path = PHOTOS_ROOT_NAME + "/" + "/".join(taxon)

    photo_count = 0
    photo_file_names = []

    gis.search(search_params=search_params)

    # Shuffle the results to get different images to be shown each time
    results = gis.results()
    random.shuffle(results)

    for image in results:
        # If the image doesn't explicitly mention the genus and species, skip it
        url_lowercase = image.url.lower()
        if taxon[1].lower() not in url_lowercase or taxon[2].lower() not in url_lowercase:
            continue

        image_file_name = image.url.split('/')[-1].split('\\')[-1]
        photo_file_names.append(image_file_name)

        # If the destination folders are missing, we must create them first
        cache_destination_path = const.CACHE_ROOT + "/" + taxon_photos_path
        if not os.path.exists(cache_destination_path):
            os.makedirs(cache_destination_path)

        # Only download if the photo isn't already cached
        cached_photos = os.listdir(cache_destination_path)
        if image_file_name not in cached_photos:
            image.download(cache_destination_path)
        else:
            print("CACHED!")

        photo_count += 1
        if photo_count >= MAX_PHOTO_COUNT:
            break

    return [taxon_photos_path + "/" + x for x in photo_file_names]

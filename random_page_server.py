import webbrowser
import os
import random
import time

import boto3
from jinja2 import Environment, FileSystemLoader

import photo_loader as pl


PHOTOS_ROOT = pl.CACHED_PHOTOS_ROOT
DYNAMODB_TABLE_NAME = "plant_flashcards-common_names"


def main():
    taxon = get_taxon()
    common_name = get_common_name(taxon[1], taxon[2])
    open_taxon_page(taxon, common_name)
    taxon_results = get_all_inputs()
    save_results(taxon, taxon_results)


def get_taxon():
    return get_random_taxon()


def get_random_taxon():
    all_taxons = pl.get_all_taxons()
    return random.choice(all_taxons)


def open_taxon_page(taxon, common_name):
    pl.ensure_photos_cached(taxon)
    
    photo_files = os.listdir(PHOTOS_ROOT + "/" + "/".join(taxon))
    photos = ["/".join(taxon) + "/" + x for x in photo_files]

    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")
    flashcard_html = template.render(
        photos=photos, family=taxon[0], genus=taxon[1], species=taxon[2], common_name=common_name)
    
    with open(PHOTOS_ROOT + "/flashcard.html", 'w') as f:
        f.write(flashcard_html)
    
    webbrowser.open(os.path.abspath(PHOTOS_ROOT + "/flashcard.html"))


def get_common_name(genus, species):
    """
    The common names are kept in a DynamoDB table; this retrieves it given a genus and species.
    """
    client = boto3.client("dynamodb")
    response = client.get_item(TableName=DYNAMODB_TABLE_NAME, Key={"Binomial": {'S': f"{genus} {species}"}})

    # The data from the item in the table is always in the 'Item' sub-dictionary
    # That sub-dictionary has the attributes as keys ('Common name' here), and values that are sub-dictionaries
    # Those sub-dictionaries have the attribute type as key ('S' here), and values that are the actual value.
    return response['Item']['Common name']['S']


def get_all_inputs():
    family_input = get_input("FAMILY")
    genus_input = get_input("GENUS")
    species_input = get_input("SPECIES")
    common_name_input = get_input("COMMON NAME")
    
    return family_input, genus_input, species_input, common_name_input


def get_input(taxon_level):
    result = input("Type '1' if you guessed " + taxon_level + " correctly, '0' otherwise.\n")
    result = "0" if result == "" else result
    return result


def save_results(taxon, taxon_results):
    with open("../flashcard_guess_results.csv", 'a') as f:
        f.write(f"{int(time.time())},{','.join(taxon)},{','.join(taxon_results)}\n")


if __name__ == "__main__":
    main()

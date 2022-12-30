import os
import random
import time
import webbrowser

import boto3
from jinja2 import Environment, FileSystemLoader

import aws_photo_loader as apl
import constants as const
import gis_photo_loader as gpl
import taxon_picker as tp


def main():
    client = boto3.client("dynamodb")

    taxon = tp.pick_taxon(client)
    common_name = get_common_name(client, taxon[1], taxon[2])

    open_taxon_page(taxon, common_name)

    taxon_results = get_all_inputs()
    save_results(client, taxon, taxon_results)


def open_taxon_page(taxon, common_name):
    # TODO For now, just use GIS photos 50% of the time
    random_value = random.random()
    if random_value < 0.5:
        photo_paths = apl.get_photo_paths(taxon)
    else:
        photo_paths = gpl.get_photo_paths(taxon)

    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")
    flashcard_html = template.render(
        photos=photo_paths, family=taxon[0], genus=taxon[1], species=taxon[2], common_name=common_name)

    # Some plant photo names will have unicode characters, so we must encode with unicode
    html_file_path = const.CACHE_ROOT + "/flashcard.html"
    with open(html_file_path, 'w', encoding="utf-8") as f:
        f.write(flashcard_html)

    webbrowser.open(os.path.abspath(html_file_path))


def get_common_name(client, genus, species):
    """
    The common names are kept in a DynamoDB table; this retrieves it given a genus and species.
    """
    response = client.get_item(
        TableName=const.DYNAMODB_COMMON_NAMES_TABLE, Key={"Binomial": {'S': f"{genus} {species}"}}
    )

    if 'Item' not in response:
        raise Exception(f"Could not retrieve common name for '{genus} {species}'!")

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
    result = False if (result == "" or result == "0") else True
    return result


def save_results(client, taxon, taxon_results):
    response = client.put_item(
        Item={
            'Binomial': {'S': f'{taxon[1]} {taxon[2]}'},
            'UnixTime-ns': {'N': str(time.time_ns())},
            'Correct-Family': {'BOOL': taxon_results[0]},
            'Correct-Genus': {'BOOL': taxon_results[1]},
            'Correct-Species': {'BOOL': taxon_results[2]},
            'Correct-CommonName': {'BOOL': taxon_results[3]},
        },
        TableName=const.DYNAMODB_GUESS_RESULTS_TABLE,
    )

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        print(f"ERROR! Could not save guess results! Response: {response}")


if __name__ == "__main__":
    main()

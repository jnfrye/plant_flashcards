import webbrowser
import os
import random
import time

import boto3
from jinja2 import Environment, FileSystemLoader

import photo_loader as pl


PHOTOS_ROOT = pl.CACHED_PHOTOS_ROOT
DYNAMODB_COMMON_NAMES_TABLE = "plant_flashcards-common_names"
DYNAMODB_GUESS_RESULTS_TABLE = "plant_flashcards-guess_results"
SECONDS_PER_DAY = 86400
NS_PER_SECOND = 1E9
MAX_GUESS_AGE_DAYS = 30
RETRY_DELAY_SECONDS = 60
RETRY_FACTOR = 4  # If a retry is correctly guessed, this is how many times the prev retry delay until another retry


class GuessResult:
    def __init__(self, binomial, unix_time_ns, family_correct, genus_correct, species_correct, common_name_correct):
        self.binomial = binomial
        self.unix_time_ns = unix_time_ns
        self.family_correct = family_correct
        self.genus_correct = genus_correct
        self.species_correct = species_correct
        self.common_name_correct = common_name_correct

    @staticmethod
    def from_response_item(item):
        result = GuessResult(
            binomial=item['Binomial']['S'],
            unix_time_ns=int(item['UnixTime-ns']['N']),
            family_correct=item['Correct-Family']['BOOL'],
            genus_correct=item['Correct-Genus']['BOOL'],
            species_correct=item['Correct-Species']['BOOL'],
            common_name_correct=item['Correct-CommonName']['BOOL'],
        )

        return result

    def is_correct(self):
        return self.family_correct and self.genus_correct and (self.species_correct or self.common_name_correct)


def main():
    client = boto3.client("dynamodb")

    taxon = get_taxon(client)
    common_name = get_common_name(client, taxon[1], taxon[2])

    open_taxon_page(taxon, common_name)

    taxon_results = get_all_inputs()
    save_results(client, taxon, taxon_results)


def get_recent_guesses(client):
    min_guess_unix_time_ns = time.time_ns() - SECONDS_PER_DAY * NS_PER_SECOND * MAX_GUESS_AGE_DAYS
    response = client.scan(
        TableName=DYNAMODB_GUESS_RESULTS_TABLE,
        IndexName="UnixTime-ns-index",
        FilterExpression="#t >= :minTime",
        ExpressionAttributeNames={"#t": "UnixTime-ns"},
        ExpressionAttributeValues={":minTime": {'N': str(min_guess_unix_time_ns)}}
    )

    if "LastEvaluatedKey" in response:
        raise Exception("NEED TO DEAL WITH LastEvaluatedKey")

    guess_results = []
    for item in response["Items"]:
        guess_results.append(GuessResult.from_response_item(item))

    return sorted(guess_results, key=lambda x: x.unix_time_ns)


def get_taxon(client):
    """
    Determine the taxon that should be guessed on.
    """
    all_taxons = pl.get_all_taxons()

    binomial = get_binomial_to_retry(client)

    if binomial is not None:
        return get_taxon_from_binomial(all_taxons, binomial)

    return random.choice(all_taxons)


def get_taxon_from_binomial(all_taxons, binomial):
    genus, species = binomial.split()
    for taxon in all_taxons:
        if taxon[1] == genus and taxon[2] == species:
            return taxon

    raise Exception(f"Could not find taxon for binomial {binomial}!")


def get_binomial_to_retry(client):
    # Note that the code below assumes the guess results list is sorted chronologically
    guess_results = get_recent_guesses(client)

    # We determine, for each recently guessed on binomial, when it should be retried.
    # To do this, first we determine what delays to use and what the most recent guess time was
    binomial_retry_delays = dict()
    binomial_most_recent_guess_times = dict()

    for x in guess_results:
        binomial_most_recent_guess_times[x.binomial] = x.unix_time_ns

        if not x.is_correct():
            binomial_retry_delays[x.binomial] = RETRY_DELAY_SECONDS * NS_PER_SECOND
        elif x.binomial in binomial_retry_delays:
            binomial_retry_delays[x.binomial] *= RETRY_FACTOR

    # If we came up with no delays, there must not have been any recent incorrect guesses.
    if len(binomial_retry_delays) == 0:
        return None

    # Then we add the delays to the most recent guess times to get the time after which it should be retried
    binomial_retry_times = dict()
    # If we didn't calculate a delay, the binomial must not have any incorrect guesses, so we don't care about it
    for binomial in binomial_retry_delays.keys():
        binomial_retry_times[binomial] = binomial_most_recent_guess_times[binomial] + binomial_retry_delays[binomial]

    # We return the binomial with the oldest retry time that is before the current time
    # To do this we just sort the retry times dict chronologically and take the first element
    oldest_retry_time_kvp = sorted(binomial_retry_times.items(), key=lambda kvp: kvp[1])[0]

    # We only return the oldest retry if it is before the present time.
    if oldest_retry_time_kvp[1] < time.time_ns():
        return oldest_retry_time_kvp[0]

    return None


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


def get_common_name(client, genus, species):
    """
    The common names are kept in a DynamoDB table; this retrieves it given a genus and species.
    """
    response = client.get_item(TableName=DYNAMODB_COMMON_NAMES_TABLE, Key={"Binomial": {'S': f"{genus} {species}"}})

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
        TableName=DYNAMODB_GUESS_RESULTS_TABLE,
    )

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        print(f"ERROR! Could not save guess results! Response: {response}")


if __name__ == "__main__":
    main()

import time
import random

import constants as const
import photo_loader as pl

MAX_GUESS_AGE_DAYS = 30
RETRY_DELAY_SECONDS = 120
RETRY_FACTOR = 5  # If a retry is correctly guessed, this is how many times the prev retry delay until another retry


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


def pick_taxon(client):
    """
    Determine the taxon that should be guessed on.
    """
    binomial = _pick_binomial_to_retry(client)

    if binomial is not None:
        return _get_taxon_from_binomial(client, binomial)

    return random.choice(pl.get_all_taxons())


def _get_taxon_from_binomial(client, binomial):
    genus, species = binomial.split()
    family = _get_family(client, genus)
    return family, genus, species


def _get_family(client, genus):
    response = client.get_item(TableName=const.DYNAMODB_GENERA_TABLE, Key={'Genus': {'S': genus}})

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f"Could not get family of {genus}! Response: {response}")

    return response['Item']['Family']['S']


def _pick_binomial_to_retry(client):
    # Note that the code below assumes the guess results list is sorted chronologically
    guess_results = _get_recent_guesses(client)

    # We determine, for each recently guessed on binomial, when it should be retried.
    # To do this, first we determine what delays to use and what the most recent guess time was
    binomial_retry_delays = dict()
    binomial_most_recent_guess_times = dict()

    for x in guess_results:
        binomial_most_recent_guess_times[x.binomial] = x.unix_time_ns

        if not x.is_correct():
            binomial_retry_delays[x.binomial] = RETRY_DELAY_SECONDS * const.NS_PER_SECOND
        elif x.binomial in binomial_retry_delays:
            binomial_retry_delays[x.binomial] *= RETRY_FACTOR

    # If we came up with no delays, there must not have been any recent incorrect guesses.
    if len(binomial_retry_delays) == 0:
        return None

    # Then we add the delays to the most recent guess times to get the time after which it should be retried
    binomial_retry_times = dict()
    # If we didn't calculate a delay, the binomial must not have any incorrect guesses, so we don't care about it
    for binomial in binomial_retry_delays.keys():
        retry_time = binomial_most_recent_guess_times[binomial] + binomial_retry_delays[binomial]

        # We only consider retry times that are in the past
        if retry_time < time.time_ns():
            binomial_retry_times[binomial] = retry_time

    # If we came up with no retry times, there must not be any binomials ready to be retried.
    if len(binomial_retry_times) == 0:
        return None

    # We return the binomial with the MOST RECENT retry time that is before the current time.
    # To do this we just sort the retry times dict chronologically and take the last element.
    oldest_retry_time_kvp = sorted(binomial_retry_times.items(), key=lambda kvp: kvp[1])[-1]
    return oldest_retry_time_kvp[0]


def _get_recent_guesses(client):
    min_guess_unix_time_ns = time.time_ns() - const.SECONDS_PER_DAY * const.NS_PER_SECOND * MAX_GUESS_AGE_DAYS
    response = client.scan(
        TableName=const.DYNAMODB_GUESS_RESULTS_TABLE,
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

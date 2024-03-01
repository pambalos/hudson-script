import datetime
import math
import os
import random
import time
import csv
import concurrent.futures as cf

import requests as requests
from threading import Lock

CARD_ID_FILE = "cards.csv"
TEST_ENDPOINT_VERSION = "v1"
TEST_ENDPOINT_RESOURCE = "cards"
TEST_ENDPOINT = "https://api.magicthegathering.io/<version>/<resource>"
DEFAULT_THREADS = 10
MAX_RETRIES = 5
MAX_WAIT = 30
WAIT = 5
PRE_REQUEST_SLEEP_RANGE = 15  # Seconds to sleep before making a request - used so we don't overload the API
OUTCOME_MESSAGES = {True: "Passed", False: "Failed", None: "Failed to get data"}
OUTCOME_LOG_FILES = {True: "passed-cards.txt", False: "mismatch-card.txt", None: "no-data.txt"}
CSV_FIELD_MAP = {"Name": "name", "Converted Mana Cost": "cmc", "Rarity": "rarity", "Set": "set", "Power": "power",
                 "Toughness": "toughness", "MultiverseId": "multiverseid", "Id": "id"}
STRING_ONLY_FIELDS = ["power", "toughness"]
NUMBER_ONLY_FIELDS = ["cmc"]
VERBOSE_TESTING = True
VERBOSE_PRINT_LOGGING = False


def get_card_info():
    data_dict = {}
    if not os.path.exists(CARD_ID_FILE):
        Exception("card_ids.txt not found. Check configuration and try again.")
    else:
        with open(CARD_ID_FILE, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                data_dict[row['Id']] = row
    return data_dict


def get_card_data_from_api(card_id):
    url = TEST_ENDPOINT.replace("<version>", TEST_ENDPOINT_VERSION).replace("<resource>", TEST_ENDPOINT_RESOURCE)
    url = f"{url}/{card_id}"
    data = make_request_with_retries(url)
    if data is None:
        return None
    else:
        return data.json().get("card")


def make_request_with_retries(url, retries=MAX_RETRIES, wait=WAIT, max_wait=MAX_WAIT):
    time.sleep(random.randint(0, 10))  # random sleep so that all threads dont request at the same time
    for i in range(1, retries + 1):
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp
        else:
            if i == retries:
                return None
            sleep_time = min(math.pow(wait, i), max_wait)
            if VERBOSE_PRINT_LOGGING:
                print(
                    f"Failed to get data from {url} after {i} retries. Waiting {sleep_time} seconds before retrying...")
            time.sleep(sleep_time)
    return None


def test_card_and_log(card_id, card_info, log_locks, time_key):
    if VERBOSE_PRINT_LOGGING:
        print(f"Testing card {card_id}...")
    card_id, success_status, message = test_card(card_id, card_info)
    log_lock = log_locks.get(success_status)
    with log_lock:
        with open(time_key + "_" + OUTCOME_LOG_FILES.get(success_status), "a") as file:
            file.write(f"Card {card_id} - {message}\n")
    return card_id, success_status, message


def test_card(card_id, card_info):
    card_data = get_card_data_from_api(card_id)
    message = ""
    if card_data is not None:
        for key in card_info:
            mapped_key = CSV_FIELD_MAP.get(key)
            test_val, fetched_val = convert_values_for_test(mapped_key, card_info.get(key), card_data.get(mapped_key))
            if test_val != fetched_val:
                if not VERBOSE_TESTING:
                    return card_id, False, (f"expected {test_val} but got {fetched_val}"
                                            f" for {mapped_key}.")
                else:
                    message += f"expected {test_val} but got {fetched_val} for {mapped_key}, "
        if message == "":
            return card_id, True, f"fetch data matches test data."
        else:
            return card_id, False, message
    else:
        return card_id, None, f"failed to get data from API with {MAX_RETRIES} retries."


# Specific rules of conversion!! - very important. This is where we add expected conversion behavior.
# In this case, the API Docs state that both 'power' and 'toughness' should only ever be strings,
# and 'cmc' should be a number.
# Testing with Python shows there could be cases where fetched data is a float, but test val is an int.
# Testing also showed improper None/blank string handling, so I added a piece to properly convert that
# There are a number of specific conversion cases like this that need to be handled.
# A good example of this is in regard to the multiverseid field.
# The API Docs do not state anything specific about it being a truncated number, but testing shows that it probably is.
# In the above case, we need to decide what we want to do with testing. Do we expect the truncated data?
# If the answer is yes, then we need to truncate the data for said key in this conversion method.
def convert_values_for_test(key, test_value, fetched_value):
    test_value_r = test_value
    fetched_value_r = fetched_value
    if key in STRING_ONLY_FIELDS:
        if isinstance(test_value, float) or isinstance(fetched_value, float):
            test_value_r = float(test_value)
            fetched_value_r = float(fetched_value)
        if isinstance(test_value, int) or isinstance(fetched_value, int):
            test_value_r = int(test_value)
            fetched_value_r = int(fetched_value)

    elif key in NUMBER_ONLY_FIELDS:
        test_value_r = float(test_value) if test_value is not None else None
        fetched_value_r = float(fetched_value) if fetched_value is not None else None
    else:
        test_value_r = str(test_value) if test_value is not None else None
        fetched_value_r = str(fetched_value) if fetched_value is not None else None

    # handle blank strings/None
    if test_value_r == "":
        test_value_r = None
    if fetched_value_r == "":
        fetched_value_r = None
    return test_value_r, fetched_value_r


def init_test_controller():
    print("Initiating test...")
    start_time = time.time()
    time_key = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    card_ids = get_card_info()
    print(f"# of Cards to test: {len(card_ids)}")

    outcomes = {key: 0 for key in OUTCOME_MESSAGES.keys()}
    log_locks = {key: Lock() for key in OUTCOME_LOG_FILES.keys()}
    processed = 0

    with cf.ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as thread_executor:
        futures = [thread_executor.submit(test_card_and_log, card_id, card_ids.get(card_id), log_locks, time_key)
                   for card_id in card_ids]
        for future in cf.as_completed(futures):
            try:
                card_id, success_status, message = future.result()
                outcomes[success_status] += 1
                processed += 1
                if VERBOSE_PRINT_LOGGING:
                    print(
                        f"Finished testing #{processed} card {card_id} - {OUTCOME_MESSAGES.get(success_status)} - {message}")
            except Exception as e:
                print(f"Async Error occurred: {e}")

    end_time = time.time()
    print(f"Testing complete. Time taken: {end_time - start_time} seconds.")
    print(
        f"Results: Passed({outcomes.get(True)}), Failed({outcomes.get(False)}), Failed GET Data({outcomes.get(None)})")
    print(f"Log files: Passed({OUTCOME_LOG_FILES.get(True)}), Failed({OUTCOME_LOG_FILES.get(False)}), "
          f"Failed GET Data({OUTCOME_LOG_FILES.get(None)})")


init_test_controller()

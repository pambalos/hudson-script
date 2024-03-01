# Hudson Interview Test Script

## Introduction
This script is designed to test the functionality of the Magic the Card Gathering API referenced at https://docs.magicthegathering.io/. It is written in Python and uses the requests library to make HTTP requests to the API. The script is designed to be run from the command line, and already has the necessary supporting files (cards.csv).

I decided to simply test the one "cards" resource endpoint as it is the most appropriate for as I am approaching this task by checking each card.

## Usage
### Running the script
1. Ensure you have the required Python packages installed: ```pip install -r requirements.txt```
2. Run the script from the command line: ```python3 magic-test.py```

### Script configuration
The script can be configured by modifying the following variables at the top of the script:
- ```TEST_ENDPOINT```: The base URL of the Magic the Card Gathering API
- ```TEST_ENDPOINT_VERSION```: The version of the API to test
- ```TEST_ENDPOINT_RESOURCE```: The resource to test
- ```DEFAULT_THREADS```: The number of threads to use for concurrent requests
- ```MAX_RETRIES```: The number of times to retry a failed request
- ```MAX_WAIT```: The maximum time to wait between retries
- ```WAIT```: The default time to wait between requests
- ```PRE_REQUEST_SLEEP_RANGE```: The range of time to sleep before making a request, needed to avoid rate limiting/overloading the API
- ```OUTCOME_MESSAGES```: The messages to display for each test outcome
- ```OUTCOME_LOG_FILES```: The log files to write for each test outcome
- ```CSV_FIELD_MAP```: The mapping of CSV fields to API fields
- ```STRING_ONLY_FIELDS```: The fields that should be treated as strings (according to API docs)
- ```NUMBER_ONLY_FIELDS```: The fields that should be treated as numbers (according to API docs)
- ```VERBOSE_TESTING```: Whether to continue testing matches after a failure is found. (Get all mismatches or first)
- ```VERBOSE_PRINT_LOGGING```: Whether to print individual thread logs or not.

### Script output
The script will write the results to log files. The log files will be named with the current date and time, and will be written to the same directory as the script.

Depending on whether you have set VERBOSE_PRINT_LOGGING to True or False, the script will output the logs of each thread to the console or not. This can be good for debugging.

Outside of that, the script will print the number of cards it is going to test, how long it took to run all the tests, and the number of each outcome.

## Write up
### Test approach
- To approach this problem I began by reading the API documentation and understanding the structure of the data. I used one of the csv entries to test manually with Postman, to view the data on the side, then compared it against the CSV data and API documentation to build a mapping of the fields.
- The above step was perhaps one of the most challenging parts to this, as field conversions and such can be a tricky thing to test properly. There were many edge cases where ints or nums were being read as strings, or vice-versa. 
- The key method for this piece - mapping data and types is my conversion method ```convert_values_for_test(key, test_value, fetched_value)```
  - This method is used for edge case 'num only' and 'string only' fields, and for the rest of the fields, it simply checks if the fetched value is equal to the test value, and upgrades them for comparison as needed.
  - It uses config lists of num and string only fields (as provided in the API docs) to determine how to handle the fields.
- One problem that I have run into with data comparison tests in the past is whether or not all data mismatches are compared, or if a single failure will stop the test.
  - To handle this, I have added a ```VERBOSE_TESTING``` flag to the config, which will allow the user to choose whether to continue testing matches after a failure is found. (Get all mismatches or first)
- I also wanted to use concurrency for testing as each card_id can be tested on its own. As such, I built this script to use threads for concurrent requests. 
  - I used the Python threading library to create a thread pool. 
  - I also added a sleep time before each request to avoid rate limiting/overloading the API.
  - I also introduced a locking mechanism to ensure that the log files are written correctly.

### Test Findings

#### Concurrency/Performance Findings 
- I tested a number of different concurrency configurations and found that it was very easy to overload the Magic API.
  - I found that 10 threads was the maximum number of threads that I could use without getting unexpected failures, even after implementing a random sleep and exponential backoff method. 
  - Implementing the random sleep before each request began helped a lot as it allowed the API to breathe a bit.
  - I had to play around with a number of different concurrency configurations before finally landing on one that is stable and reliable; ```DEFAULT_THREADS = 10, MAX_RETRIES = 5, MAX_WAIT = 30, WAIT = 5, PRE_REQUEST_SLEEP_RANGE = 10```

#### Data Findings
- There were a number of data findings worth reporting;
  - All of the cmc values seemed to be off by 1. (Caused all records to fail)
  - The multiverseid field seemed to always be a truncated value of the equivalent csv field. (If truncated, should truncate test data) (Also caused all records to fail)

#### Lessons Learned
- Definitely have to be extra careful about overloading APIs when running tests like this - many of my original test configurations were causing irregular failed to GET data responses.
- I didn't spend a ton of time on my ```convert_values_for_test(key, test_value, fetched_value)``` method, but I think it could be improved. It's a bit of a mess right now, and I think it could definitely be cleaned up a bit.

#### Future Improvements
- If I had more time I would clean up and clarify the conversion and mapping rules method.
- I would probably also add argument parsing to the script to allow for more flexible testing.
- I would also adjust the script to be able to test other endpoints, and not just the cards resource endpoint.


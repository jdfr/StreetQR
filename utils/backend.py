from firebase import firebase
import datetime
import json
import warnings
import time

fb = firebase.FirebaseApplication("https://smart-campus-uma.firebaseio.com/", None)


def post_minute_data(data, fb):
        # Records people on Firebase by day and minute

        # Get timing
        now = datetime.datetime.now()
        day = now.date()
        hour_min = now.strftime("%H:%M")
        print(hour_min)
        # Convert Data Dict to JSON
        data_json = json.dumps(data)
        # Set variable dinamically
        url = str('/streetqr/counter/' + str(day) + '/')
        # Post Data
        try:
                fb.patch(url, {hour_min: data_json})
        except:
                warnings.warn('Failed to POST data')


def post_daily_data(data, fb):
        # Records people on Firebase by day and minute

        # Get timing
        # yesterday = datetime.datetime.now().date() - datetime.timedelta(1)
        # Set variable dinamically
        url = str('/streetqr/counter/total/')
        data_json = json.dumps(data)

        # Post Data
        try:
                fb.patch(url, {'total': data_json})

        except:
                print('Failed to POST daily data')


def write_last_data_taken(data):

        # Filename to write
        filename = "data.txt"
        # Open the file with writing permission
        data_file = open(filename, 'w')
        # Convert data to string form
        data_str = json.dumps(data)
        # Write a line to the file
        data_file.write(data_str)
        # Close the file
        data_file.close()


def get_last_data_taken():
        # Filename to write
        filename = "data.txt"
        # Open the file with reading permission
        data_file = open(filename, 'r')
        if data_file.mode == 'r':
                data_str = data_file.read()
                data = json.loads(data_str)
                return data

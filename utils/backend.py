from firebase import firebase
import datetime
import json
import warnings
import time

fb = firebase.FirebaseApplication("https://smart-campus-uma.firebaseio.com/", None)


def post_people_data(data, fb):
        # Records people on Firebase by day and minute

        # Get timing
        now = datetime.datetime.now()
        day = now.date()
        hour_min = now.strftime("%H:%M")
        # Convert Data Dict to JSON
        data_json = json.dumps(data)
        # Set variable dinamically
        url = str('/streetqr/counter/' + str(day) + '/')
        # Post Data
        try:
                fb.patch(url, {hour_min: str(data_json)})
        except:
                warnings.warn('Failed to POST data')


def post_people_data_full_day(data,  fb):
        # Records people on Firebase by day and minute

        # Get timing
        yesterday = datetime.datetime.now().date() - datetime.timedelta(1)
        # Set variable dinamically
        url = str('/streetqr/counter/' + str(yesterday) + '/')
        # Post Data
        try:
                fb.patch(url, {'total': str(data)})

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


if __name__ == '__main__':
        
        fb = firebase.FirebaseApplication("https://smart-campus-uma.firebaseio.com/", None)
        post_people_data(2, fb)

import calendar
from datetime import datetime, timedelta
import requests
import json
import pandas as pd


# Define the year for which you want to retrieve data
year = 2023  # Change this to the desired year

#   DEFINE SPORTS
sports = ["Baseball", "Basketball", "FieldHockey", "Football", "Hockey", "Lacrosse", "Soccer", "Softball", "Volleyball"]
# Set the base URL of your REST API
base_url = "https://tourneymachine.com/Public/Service/json/TournamentSearch.aspx"

# Initialize an empty JSON object to store the results
result_set = {}

# Loop through each month
for sport in sports:
    for month in range(1, 13):
        # Calculate the first day and last day of the month
        start_date = datetime(year, month, 1) 
        _,last_day = calendar.monthrange(year, month) 
        end_date = datetime(year, month, last_day)    
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        # Construct the URL with the start_date and end_date parameters
        url = f"{base_url}?sport={sport}&start={start_date}&end={end_date}"        
        # print(start_date, end_date)
        # print(url)
        # key = f"{sport}-{start_date}"
        # Make the GET request
        response = requests.get(url)
    
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response and append it to the result set
            result_set.update(response.json())
            # Should be an append
        else:
            print(f"Failed to retrieve data for {start_date} - {last_day}. Status code: {response.status_code}")

# Save the result set to a JSON flatfile
with open("result_set.json", "w") as json_file:
    json.dump(result_set, json_file, indent=2)

print("Data retrieval and saving complete.")

col_name = ["IDTournament", "Sport", "Location","StartDate"]
num_events_per_sport = pd.DataFrame(columns = col_name)

for k, v in result_set.items():
    # print(k, v["Sport"],v["DisplayLocation"])
    num_events_per_sport.loc[len(num_events_per_sport)] = [k, v["Sport"],v["DisplayLocation"],v["StartDate"]]

print(num_events_per_sport)

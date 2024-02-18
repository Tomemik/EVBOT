import os.path
import os
import discord
import numpy as np
import pandas as pd
import re

from enum import Enum
from discord.ext import commands
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1XlfQsxaVI1XSYFXAlL7r5j_vqahGzgr_UCxMvfH4jRA"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)
CHANNEL_ID = 1208376845427413042

def connect():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


Teams = {
    "All Stars": 0,
    "Anzio": 1,
    "BC Freedom": 2,
    "Bellwall": 3,
    "Bonple": 4,
    "Blue Division": 5,
    "Chi-Ha-Tan": 6,
    "Count": 7,
    "Gregor": 8,
    "Jatkosota": 9,
    "Kebab": 10,
    "Koala": 11,
    "Kuromorimine": 12,
    "Maginot": 13,
    "Maple": 14,
    "Ooarai": 15,
    "Pravda": 16,
    "Saint Gloriana": 17,
    "Saunders": 18,
    "Tategoto": 19,
    "Viggen": 20,
    "Waffle": 21,
    "West Kureouji": 22,
    "Yogurt": 23
}


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


reward_colors = {
    "Match Reward": "#9fc5e8",
    "Judge Reward": "#3c78d8",
    "Sub": "#ffe599"
}

def extract_rewards(message_content):
    rewards = {
        'Match Reward': {},
        'Judge Reward': {},
        'Sub': {}
    }


    team_names = []


    # Regular expression pattern to Match Reward team name and reward value
    pattern = r'([A-Za-z0-9\s-]+):\s+\+(\d+)'

    # Extracting Match Reward Rewards
    match_rewards = re.search(r'Match Reward:\n(.*?)Judge Reward:', message_content, re.DOTALL)
    print(match_rewards.group(1))
    if match_rewards:
        match_reward_data = match_rewards.group(1)
        # Loop through each team
        for team in Teams.keys():
            # Check if the team is present before or after the '\n'
            if team in match_reward_data.split('\n')[0]:
                rewards['Match Reward'][team] = int(re.search(r':\s*\+(\d+)\s+each$', match_reward_data.split('\n')[0]).group(1))
            elif team in match_reward_data.split('\n')[1]:
                rewards['Match Reward'][team] = int(re.search(r':\s*\+(\d+)\s+each$', match_reward_data.split('\n')[1]).group(1))


    # Extracting Judge Reward Rewards
    judge_rewards = re.search(r'Judge Reward:\s*([\w\s]+)?\s*\n(.*?)Sub Reward:', message_content, re.DOTALL)
    if judge_rewards:
        judge_name, judge_data = judge_rewards.groups()
        judge_results = re.findall(pattern, judge_data)
        for team, reward in judge_results:
            rewards['Judge Reward'][team.strip()] = int(reward)

    # Extracting Sub Rewards
    sub_rewards = re.findall(r'Sub Reward:\n(.*?)$', message_content, re.DOTALL)
    if sub_rewards:
        sub_results = re.findall(pattern, sub_rewards[0])
        for team, reward in sub_results:
            rewards['Sub'][team.strip()] = int(reward)

    return rewards


def get_school_row(sheet_service, offset):
    api_range = f"E{4+offset}:BEW{4+offset}"
    try:
        sheet = sheet_service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range="Testing!" + api_range)
            .execute()
        )

        values = result.get("values", [])

        if not values:
            print("No data found.")
            return

        return values

    except HttpError as err:
        print(f"An error occurred: {err}")
        return None


def get_first_empty(sheet_service, team):
    creds = connect()
    if creds:
        service = sheet_service
        row_data = get_school_row(service, Teams[team])[0]

        if row_data is not None:
            # Iterate through the row data to find the index of the first empty cell
            for i, cell in enumerate(row_data):
                if not cell:  # Check if cell is empty
                    # Return the index of the first empty cell
                    return i
            # If no empty cell is found, return the index after the last column
            return len(row_data)
        else:
            print("No row data found.")
            return -1
    else:
        print("Failed to connect.")
        return -1


def update_first_empty_cell(sheet_service, team, value, reward_type):
    # Get the index of the first empty cell for the specified team
    empty_cell_index = get_first_empty(sheet_service, team)

    # Ensure that an empty cell was found
    if empty_cell_index >= 0:
        try:
            # Convert the index to a column letter
            column_letter = to_column_letter(empty_cell_index + 4)

            # Construct the range of the empty cell
            range_name = f"Testing!{column_letter}{4 + Teams[team]}"

            # Prepare the value to be written to the cell
            formatted_value = f"{value} [{reward_type}]"
            body = {"values": [[formatted_value]]}

            # Update the empty cell with the desired value
            result = (
                sheet_service.spreadsheets()
                .values()
                .update(spreadsheetId=SPREADSHEET_ID, range=range_name, valueInputOption="RAW", body=body)
                .execute()
            )

            # Apply cell formatting
            cell_format = {
                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}  # Default color (white)
            }

            # Check if reward type has a defined color
            if reward_type in reward_colors:
                rgb_color = hex_to_rgb(reward_colors[reward_type])
                cell_format["backgroundColor"] = {"red": rgb_color[0], "green": rgb_color[1], "blue": rgb_color[2]}

            # Apply the cell formatting to the specific cell
            format_result = (
                sheet_service.spreadsheets()
                .batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": [{"repeatCell": {
                    "range": {"sheetId": 788805189, "startRowIndex": 4 + Teams[team] - 1, "endRowIndex": 4 + Teams[team],
                              "startColumnIndex": empty_cell_index + 4, "endColumnIndex": empty_cell_index + 5},
                    "cell": {"userEnteredFormat": cell_format},
                    "fields": "userEnteredFormat.backgroundColor"
                }}]})
                .execute()
            )

            print(f"Updated cell {column_letter}{4 + Teams[team]} with value: {formatted_value}")

        except HttpError as err:
            print(f"An error occurred: {err}")
    else:
        print("No empty cells found in the row.")


def to_column_letter(n):
    """Converts 0-based index to spreadsheet column letter."""
    letters = ""
    while n >= 0:
        letters = chr(n % 26 + 65) + letters
        n = n // 26 - 1
    return letters

@bot.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID:
        creds = connect()
        if creds:
            service = build("sheets", "v4", credentials=creds)

            # Extract rewards from the message content
            rewards = extract_rewards(message.content)
            print(rewards)
            for category, reward in rewards.items():
                for team, value in reward.items():
                    # Update the first empty cell for each team with its corresponding value and reward type
                    update_first_empty_cell(service, team, value, category)
        else:
            print("Failed to connect to Google Sheets API")


def main():
    creds = connect()
    service = build("sheets", "v4", credentials=creds)
    bot.run(TOKEN)




if __name__ == "__main__":
    main()

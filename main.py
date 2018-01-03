from oauth2client.service_account import ServiceAccountCredentials
import json
import time
from httplib2 import Http
import os

import requests
from apiclient import discovery

TYPE_KEY_MAP = {
    "1": ["dest", "identifier", "role", "type", "verkey"],
    "101": ["data", "identifier", "reqId", "signature", "txnTime"],
    "102": [
        "data",
        "identifier",
        "ref",
        "reqId",
        "signature",
        "signature_type",
        "txnTime"
    ]
}


def update_sheets():
    # spreadsheetId = '13rFVDdfoJOLipB6upo46O9_QyDBWrhemexUo34LuX3A'
    spreadsheetId = os.environ['GOOGLE_SHEETS_ID']

    # Obtain access to google sheets api
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        os.path.abspath('./client_secret.json'), scopes)
    http_auth = credentials.authorize(Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build(
        'sheets', 'v4', http=http_auth, discoveryServiceUrl=discoveryUrl)

    # Write headers
    for record_type in TYPE_KEY_MAP:
        body = {'values': [
            TYPE_KEY_MAP[record_type]
        ]}

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheetId,
            range='Type%s!1:1' % (record_type),
            body=body,
            valueInputOption="RAW").execute()

    # Get ledger data from BCOVRIN
    ledger_response = requests.get('http://138.197.170.136/ledger/domain')
    for line in ledger_response.text.split('\n'):
        try:
            ledger_entry = json.loads(line)
        except json.decoder.JSONDecodeError:
            continue

        sequence_number = ledger_entry[0]
        content = ledger_entry[1]

        body = {
            'values': [[
                # str(item[1]) for item in sorted(content.items())
                str(content[key]) if key in content else ""
                for key in TYPE_KEY_MAP[content['type']]
            ]]
        }

        print('-Sending entry to Google Sheets-')
        print('Range: Type%s!%s:%s' % (
            content['type'], sequence_number, sequence_number))
        print('Body: ' + str(body))

        # Write ledger entries
        service.spreadsheets().values().update(
          spreadsheetId=spreadsheetId,
          range='Type%s!%s:%s' % (
            content['type'], sequence_number+1, sequence_number+1),
          body=body,
          valueInputOption="RAW").execute()

        # Avoid rate limiting
        time.sleep(0.2)


def main():
    while(True):
        update_sheets()
        time.sleep(60)


if __name__ == '__main__':
    main()

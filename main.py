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

        # Get the type
        entity_type = content['type']

        # Handle each type differently
        if entity_type == "1":
            # This ledger item is an identity

            # For each of the attributes in this data type,
            # extract the value into a variable. If the attribute
            # isn't found in the data, use "" instead so that
            # program doesn't exit with an error

            dest = content['dest'] if 'dest' in content else ""
            role = content['role'] if 'role' in content else ""
            verkey = content['verkey'] if 'verkey' in content else ""
            identifier = content['identifier'] if 'identifier' in content else ""

            # We can transform the data as needed here. For example, if we wanted to
            # change the role number into a human readable role name we could do:

            # This should probably be at the top of the file if you use this.
            ROLE_MAP = {
                "0": "Trustee",
                "2": "Steward",
                "101": "Trust Anchor"
            }

            label = 'did: %s' % dest
            role_name = ROLE_MAP[role] if role in ROLE_MAP else "No Role"

            # We build a row in the spreadsheet. We can have as many columns as we want
            # for each row. Each entry in the array is a new column.

            # Here we can use our transformed data and create new rows as needed!
            row = [label, role_name]

        elif entity_type == "101":
            # This ledger item is a schema
            pass
        elif entity_type == "102":
            # This ledger item is a claim definition
            pass

        # We build the expected request format using the row above
        body = {'values': [row]}
        
        # body = {
        #     'values': [[
        #         # str(item[1]) for item in sorted(content.items())
        #         str(content[key]) if key in content else ""
        #         for key in TYPE_KEY_MAP[content['type']]
        #     ]]
        # }

        # print('-Sending entry to Google Sheets-')
        # print('Range: Type%s!%s:%s' % (
        #     content['type'], sequence_number, sequence_number))
        # print('Body: ' + str(body))

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

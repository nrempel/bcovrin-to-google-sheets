from oauth2client.service_account import ServiceAccountCredentials
import json
import time
from httplib2 import Http
import os

import requests
from apiclient import discovery

ELEMENTS_HEADERS = ['Label', 'Type', 'Tags', 'Description']
CONNECTIONS_HEADERS = ['From', 'To', 'Label', 'Type', 'Tags', 'Description']

TYPE_MAP = {
    "1": "Identity",
    "101": "Schema",
    "102": "Claim Definition"
}

ROLE_MAP = {
    "0": "Trustee",
    "2": "Steward",
    "101": "Trust Anchor"
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

    # We will use 2 worksheets:
    # Elements and Connections

    # Write elements headers
    body = {'values': [ELEMENTS_HEADERS]}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheetId,
        range='Elements!1:1',
        body=body,
        valueInputOption="RAW").execute()

    # Write connections headers
    body = {'values': [CONNECTIONS_HEADERS]}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheetId,
        range='Connections!1:1',
        body=body,
        valueInputOption="RAW").execute()

    # Get ledger data from BCOVRIN
    ledger_response = requests.get('http://138.197.170.136/ledger/domain')

    # We iterate over the data 2 times.
    # The first time, we write all elements of all types.
    # The second time, iterate over each element and compare
    # it to every other element in order to create the relationships
    # in a nested loop.

    # First we iterate entire data set and create elements
    row_num = 1
    for line in ledger_response.text.split('\n'):
        row_num += 1
        try:
            ledger_entry = json.loads(line)
        except:
            # Just ignore json decode errors for now
            continue

        sequence_number = ledger_entry[0]
        content = ledger_entry[1]

        # Let's extract some data from the ledger content

        # For the label we use the 'dest' attribute. But if that doesn't
        # exist, let's use sequence number instead.
        Label = content['dest'] if 'dest' in content else sequence_number
        type_number = content['type'] if 'type' in content else ""
        # We want the human-readable type name
        Type = TYPE_MAP[type_number]
        Description = str(content['data']) if 'data' in content else ""

        # Now we write this row two the "Elements" worksheet
        # using row_num as the google sheets row

        # We use empty strings to make empty cells
        # to make sure we match the format of ELEMENTS_HEADERS
        entity_row = [Label, Type, "", Description]

        body = {'values': [entity_row]}

        print('-Sending entry to Google Sheets-')
        print('Elements!%s:%s' % (row_num, row_num))
        print('Body: ' + str(body))

        # Write ledger entries
        service.spreadsheets().values().update(
          spreadsheetId=spreadsheetId,
          range='Elements!%s:%s' % (row_num, row_num),
          body=body,
          valueInputOption="RAW").execute()

        # Avoid rate limiting
        time.sleep(0.5)

    # Second, we iterate over every ledger entry and
    # compare to all other ledger entries
    row_num = 1
    for line in ledger_response.text.split('\n'):
        try:
            ledger_entry = json.loads(line)
        except:
            # Just ignore json decode errors for now
            continue

        current_element = ledger_entry[1]

        for line in ledger_response.text.split('\n'):
            try:
                ledger_entry = json.loads(line)
            except:
                # Just ignore json decode errors for now
                continue

            compared_element = ledger_entry[1]
            compared_element_sequence_number = ledger_entry[0]

            current_element_type = current_element['type']

            current_element_dest = current_element['dest'] \
                if 'dest' in current_element else ""
            compared_element_identifier = compared_element['identifier'] \
                if 'identifier' in compared_element else ""

            # Let's compare the "dest" attribute of the current element
            # to the "identifier" element to the currently compared element.
            # If they are the same, then they are related! If that is the case,
            # we create a new relationship of that type

            # Let's handle relationships for "identifier" relationship
            if current_element_dest == compared_element_identifier:
                row_num += 1
                # The compared element's label is its 'dest'
                compared_element_dest = compared_element['dest'] \
                    if 'dest' in compared_element else ""

                From = current_element_dest
                To = compared_element_dest or compared_element_sequence_number

                # Let's make sure this matches the header format for this
                # sheet
                connections_row = [From, To, "", "Identity/Entity", "", ""]

                body = {'values': [connections_row]}

                print('-Sending entry to Google Sheets-')
                print('Elements!%s:%s' % (row_num, row_num))
                print('Body: ' + str(body))

                # Write ledger entries
                service.spreadsheets().values().update(
                  spreadsheetId=spreadsheetId,
                  range='Connections!%s:%s' % (row_num, row_num),
                  body=body,
                  valueInputOption="RAW").execute()

                # Avoid rate limiting
                time.sleep(0.5)

            # TODO: handle other relationship types
            # elif ...


def main():
    while(True):
        update_sheets()
        time.sleep(300)


if __name__ == '__main__':
    main()

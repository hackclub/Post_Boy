import requests
import json
import yaml
env = yaml.load(open('.env', 'r'))

airtable_key = env['airtable-key']

auth_header = {
        'Authorization': 'Bearer ' + airtable_key,
    }

def getPackages(slack_id, is_node_master=False):

    headers = auth_header

    params = (
        ('view', 'Everything'),
        ('filterByFormula', '\"<@'+slack_id+'>\" = {Receiver Message Tag}'),
        ('fields[]', 'Unique Index'),
        ('fields[]', 'Scenario Name'),
        ('fields[]', 'Receiver Address'),
        ('fields[]', 'Created Time'),
        ('fields[]', 'Scenario'),
        ('fields[]', 'Sender Message Tag'),
        ('fields[]', 'Tracking Number'),
        ('fields[]', 'Notes'),
        ('fields[]', 'Receiver Name'),
        ('fields[]', 'Receiver Message Tag'),
        ('fields[]', 'Status'),
    )

    response = requests.get('https://api.airtable.com/v0/apptEEFG5HTfGQE7h/Mail%20Missions', headers=headers, params=params)
    return convertRequestToPackages(response)

def getAddress(record_id):
    headers = auth_header

    response= json.loads(requests.get('https://api.airtable.com/v0/apptEEFG5HTfGQE7h/Addresses/' + record_id,
                        headers=headers).content)['fields']

    return (response['Formatted Address'], response['Update Form URL'])


def getContents(record_id):
    headers = auth_header

    response = json.loads(requests.get('https://api.airtable.com/v0/apptEEFG5HTfGQE7h/Mail%20Scenarios/' + record_id,
                        headers=headers).content)['fields']
    return response['Contents']

def is_node_master(slack_id):
    headers = auth_header

    params = (
        ('view', 'Grid view'),
        ('filterByFormula', '{Slack ID} = \"' + slack_id + "\""),
    )

    response = json.loads(requests.get('https://api.airtable.com/v0/apptEEFG5HTfGQE7h/Mail%20Senders', headers=headers,
                            params=params).content)['records']
    return len(response) == 1

def convertRequestToPackages(response):
    packages = []
    request = json.loads(response.content)['records']
    for item in request:
        package = {}
        fields = item['fields']
        package['package'] = fields['Unique Index']
        package['labels'] = fields['Scenario Name']
        package['address'],package['address_change'] = getAddress(fields['Receiver Address'][0])
        package['date_ordered'] = fields['Created Time']
        package['contents'] = getContents(fields['Scenario'][0])
        package['node_master'] = '' if 'Sender Message Tag' not in fields else fields['Sender Message Tag'][2:-1]
        package['tracking_num'] = '' if 'Tracking Number' not in fields else fields['Tracking Number']
        package['note'] = '' if 'Notes' not in fields else fields['Notes']
        package['recipient'] = {"name": fields['Receiver Name'][0], "id": fields['Receiver Message Tag'][0][2:-1]}
        package['status'] = {'10 Dropped':"NAP", '6 Delivered':'A', '5 Shipped': 'S', '4 Shipped': 'S', '3 Purchased': 'NS', '2 Assigned': 'NS', '1 Unassigned':'PAP'}[fields['Status']]
        packages.append(package)
    return packages
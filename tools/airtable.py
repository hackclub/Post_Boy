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
        ("select",
         '{"view":"Everything",'
         '"filterByFormula":"\'<@' + slack_id + '>\' = {Receiver Message Tag}",'
                                                '"fields":["Unique Index","Scenario Name","Receiver Address",'
                                                '"Created Time","Scenario","Sender Message Tag","Tracking URL",'
                                                '"Notes","Receiver Name","Receiver Message Tag","Status"]}'),
    )

    response = requests.get("https://api2.hackclub.com/v0/Operations/Mail%20Missions", headers=headers, params=params)
    return convertRequestToPackages(response)


def getAddress(record_id):
    headers = auth_header

    response = json.loads(requests.get(
        'http://api2.hackclub.com/v0/Operations/Addresses?select={"maxRecords":1,"filterByFormula":"\'' + record_id + '\' = {Record ID}"}',
        headers=headers).content)

    response = response[0]['fields']
    return (response['Formatted Address'], response['Update Form URL'])


def getContents(record_id):
    headers = auth_header

    response = json.loads(requests.get(
        'http://api2.hackclub.com/v0/Operations/Mail%20Scenarios?select={"maxRecords":1,"filterByFormula":"\'' + record_id + '\' = {Record ID}"}',
        headers=headers).content)[0]['fields']
    return response['Contents']


def is_node_master(slack_id):
    headers = auth_header

    params = (
        ('select', '{"filterByFormula":"\'<@' + slack_id + '>\' = {Slack ID}"}'),
    )

    response = requests.get('https://api2.hackclub.com/v0/Operations/Mail%20Senders', headers=headers,
                            params=params).content
    return len(response) == 1


def convertRequestToPackages(response):
    packages = []
    request = json.loads(response.content)
    for item in request:
        package = {}
        fields = item['fields']
        package['package'] = fields['Unique Index']
        package['labels'] = fields['Scenario Name']
        package['address'], package['address_change'] = getAddress(fields['Receiver Address'][0])
        package['date_ordered'] = fields['Created Time']
        package['contents'] = getContents(fields['Scenario'][0])
        package['node_master'] = '' if 'Sender Message Tag' not in fields else fields['Sender Message Tag'][2:-1]
        package['tracking_url'] = '' if 'Tracking URL' not in fields else fields['Tracking URL']
        package['note'] = '' if 'Notes' not in fields else fields['Notes']
        package['recipient'] = {"name": fields['Receiver Name'][0], "id": fields['Receiver Message Tag'][0][2:-1]}
        package['status'] = \
            {'10 Dropped': "NAP", '6 Delivered': 'A', '5 Shipped': 'S', '4 Shipped': 'S', '3 Purchased': 'NS',
             '2 Assigned': 'NS', '1 Unassigned': 'PAP'}[fields['Status']]
        packages.append(package)
    return packages
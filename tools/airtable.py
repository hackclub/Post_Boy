import requests
import json
import os
import time

airtable_key = os.getenv('AIRTABLE_KEY')


def getPackages(slack_id, is_node_master=False):
    if is_node_master:
        params = (
            ("select",
             '{"view":"Everything",'
             '"filterByFormula":"\'<@' + slack_id + '>\' = {Sender Message Tag}",'
                                                    '"fields":["Unique Index","Scenario Name","Receiver Address",'
                                                    '"Created Time","Receiver Scan Time","Sender Scan Time","Scenario","Sender Message Tag","Tracking URL",'
                                                    '"Notes","Receiver Name","Receiver Message Tag","Status"]}'),
            ('authKey', airtable_key),
        )

        response = requests.get("https://api2.hackclub.com/v0.1/Operations/Mail%20Missions",
                                params=params)
        f = open("dev.log", "w")
        f.write(json.dumps(json.loads(response.content)))
        f.close()
        return convertRequestToPackages(response)
    else:
        params = (
            ("select",
             '{"view":"Everything",'
             '"filterByFormula":"\'<@' + slack_id + '>\' = {Receiver Message Tag}",'
                                                    '"fields":["Unique Index","Scenario Name","Receiver Address",'
                                                    '"Created Time","Receiver Scan Time","Sender Scan Time","Scenario","Sender Message Tag","Tracking URL",'
                                                    '"Notes","Receiver Name","Receiver Message Tag","Status"]}'),
            ('authKey', airtable_key),
        )

        response = requests.get("https://api2.hackclub.com/v0.1/Operations/Mail%20Missions", 
                                params=params)
        f = open("dev.log", "w")
        f.write(json.dumps(json.loads(response.content)))
        f.close()
        return convertRequestToPackages(response)


def getMailScenario(name, slack_id=None):
    response = json.loads(requests.get(
        'http://api2.hackclub.com/v0.1/Operations/Mail%20Scenarios?authKey='+airtable_key+'&select={"maxRecords":1,"filterByFormula":"\'' + name + '\' = {ID}"}').content)[0]['fields']
    scenario = {}
    scenario['name'] = response['Name']
    scenario['contents'] = response['Contents']
    scenario['labels'] = response['Name']
    if slack_id:
        scenario['address'], scenario['address_change'] = getAddress(slack_id, idType='slack_id')
    return scenario


def getAddress(id, idType="record_id"):
    if idType == 'record_id':
        response = json.loads(requests.get(
            'http://api2.hackclub.com/v0.1/Operations/Addresses?authKey='+airtable_key+'&select={"maxRecords":1,"filterByFormula":"\'' + id + '\' = {Record ID}"}'
            ).content)[0]['fields']

        return (response['Formatted Address'], response['Update Form URL'])
    elif idType == 'slack_id':
        response = json.loads(requests.get(
            'http://api2.hackclub.com/v0.1/Operations/Addresses?authKey='+airtable_key+'&select={"maxRecords":1,"filterByFormula":"\'<@' + id + '>\' = {Sender Message Tag}"}').content)[0]['fields']


        return (response['Formatted Address'], response['Update Form URL'])


def getContents(record_id):
    response = json.loads(requests.get(
        'http://api2.hackclub.com/v0.1/Operations/Mail%20Scenarios?authKey='+airtable_key+'&select={"maxRecords":1,"filterByFormula":"\'' + record_id + '\' = {Record ID}"}').content)[0]['fields']
    return response['Contents']


def is_node_master(slack_id):
    params = (
        ('select', '{"filterByFormula":"\'' + slack_id + '\' = {Slack ID}"}'),
        ('authKey', airtable_key),
    )

    response = json.loads(requests.get('https://api2.hackclub.com/v0.1/Operations/Mail%20Senders',
                                       params=params).content)
    return len(response) == 1


def convertRequestToPackages(response):
    packages = []
    request = json.loads(response.content)
    for item in request:
        package = {}
        fields = item['fields']
        package['package'] = fields['Unique Index']
        package['labels'] = fields['Scenario Name'][0]
        package['address'], package['address_change'] = getAddress(fields['Receiver Address'][0])
        package['date_ordered'] = fields['Created Time']
        package['date_shipped'] = fields['Sender Scan Time'] if 'Sender Scan Time' in fields else ''
        package['date_arrived'] = fields['Receiver Scan Time'] if 'Receiver Scan Time' in fields else ''
        package['contents'] = getContents(fields['Scenario'][0])
        package['node_master'] = '' if 'Sender Message Tag' not in fields else fields['Sender Message Tag'][2:-1]
        package['tracking_url'] = '' if 'Tracking URL' not in fields else fields['Tracking URL']
        package['recipient'] = {"name": fields['Receiver Name'][0], "id": fields['Receiver Message Tag'][0][2:-1]}
        package['status'] = \
            {'10 Dropped': "NAP", '6 Delivered': 'A', '5 Shipped': 'S', '4 Shipped': 'S', '3 Purchased': 'NS',
             '2 Assigned': 'NS', '1 Unassigned': 'PAP'}[fields['Status']]
        packages.append(package)
    return packages


def isLeader(slack_id):
    params = (
        ('select', '{"filterByFormula":"\'' + slack_id + '\' = {Slack ID}"}'),
        ('authKey', airtable_key),
    )


    response = json.loads(requests.get('https://api2.hackclub.com/v0.1/Operations/People',params=params).content)
    print(response)
    return len(response) != 0 and 'Clubs' in response[0]['fields'] and len(response[0]['fields']['Clubs']) > 0
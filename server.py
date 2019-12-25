import requests
import os
import json
import slack
import yaml
import datetime
from bs4 import BeautifulSoup

from flask import Flask, request, render_template, send_from_directory

app = Flask(__name__)

env = yaml.load(open('.env', 'r'))

client_id = env['client-id']
client_secret = env['client-secret']
sign_secret = env['sign-secret']
veri_token = env['veri-token']
auth_token = env['auth-token']


@app.route("/")
def index():
    with open('index.html', 'r') as myfile:
        return myfile.read()

@app.route('/img/<path>')
def send_assets(path):
    return send_from_directory('img', path)

@app.route('/<path>')
def send_style(path):
    return send_from_directory('static', path)

@app.route('/user', methods=["GET", "POST"])
def user():
    # # Retrieve the auth code from the request params
    # auth_code = request.args['code']
    #
    # # An empty string is a valid token for this request
    # client = slack.WebClient(token="")
    #
    # # Request the auth tokens from Slack
    # response = client.oauth_v2_access(
    #     client_id=client_id,
    #     client_secret=client_secret,
    #     code=auth_code
    # )
    #
    # user_client = slack.WebClient(token=response['access_token'])
    # info = user_client.users_info()
    info = {'user':{'id':'UJ9864R4N', 'real_name':'Frank Hui'}}
    user_slack_id = info['user']['id']
    user_name = info['user']['real_name']
    packages = []
    isNodeMaster = False
    with open('database.json') as json_file:
        database = json.load(json_file)
    if user_slack_id in database:
        for package in database[user_slack_id]:
            if 'type' in package.keys() and not package['type'] == 'receiver':
                isNodeMaster = True
            elif 'type' not in package.keys():
                if package['date_shipped'] is not "NS":
                    package['date_shipped'] = datetime.datetime.utcfromtimestamp(1347517370).strftime(
                    '%Y-%m-%d %H:%M:%S') + " UTC"
                if package['date_arrived'] is not "NA":
                    package['date_shipped'] = datetime.datetime.utcfromtimestamp(1347517370).strftime(
                    '%Y-%m-%d %H:%M:%S') + " UTC"
                packages.append(package)

    else:
        return "User not in database."

    if len(packages) == 0:
        return "No packages found."
    num_of_packages = len(packages)
    return render_template("statuslist.html", packages=packages, name=user_name, len=num_of_packages)

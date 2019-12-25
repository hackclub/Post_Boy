import requests
import os
import json
import slack
import yaml
import datetime
from bs4 import BeautifulSoup
import time

from flask import Flask, request, render_template, send_from_directory, session

app = Flask(__name__)
app.secret_key = '\xf0"b1\x04\xe0.[?w\x0c(\x94\xcdh\xc1yq\xe3\xaf\xf2\x8f^\xdc'
env = yaml.load(open('.env', 'r'))

client_id = env['client-id']
client_secret = env['client-secret']
sign_secret = env['sign-secret']
veri_token = env['veri-token']
auth_token = env['auth-token']

with open('database.json') as json_file:
    database = json.load(json_file)


@app.route("/")
def index():
    if 'id' not in session:
        return render_template("index.html")
    else:
        return user()


@app.route('/img/<path>')
def send_assets(path):
    return send_from_directory('img', path)


@app.route('/<path>')
def send_style(path):
    return send_from_directory('static', path)


@app.route('/user', methods=["GET", "POST"])
def user():
    if 'id' not in session:
        # Retrieve the auth code from the request params
        auth_code = request.args['code']

        # An empty string is a valid token for this request
        client = slack.WebClient(token="")
        print(client_id)
        # Request the auth tokens from Slack
        response = client.oauth_access(client_id=client_id, client_secret=client_secret, code=auth_code)

        user_client = slack.WebClient(token=response['access_token'])
        info = user_client.users_identity()
        print(info)
        # info = {'user':{'id':'UJ9864R4N', 'real_name':'Frank Hui'}}
        user_slack_id = info['user']['id']
        user_name = info['user']['name']
        session['id'] = user_slack_id
        session['name'] = user_name
    else:
        user_slack_id = session['id']
        user_name = session['name']
    packages = []
    num_of_packages = 0
    isNode_Master = False
    client = slack.WebClient(token=auth_token)
    if user_slack_id in database:
        for package in database[user_slack_id]:
            temp_package = package.copy()
            if 'type' in package.keys() and not package['type'] == 'receiver':
                isNode_Master = True
                break
            elif 'type' not in package.keys():
                if package['date_shipped'] != "NS":
                    temp_package['date_shipped'] = datetime.datetime.utcfromtimestamp(package['date_shipped']).strftime(
                        '%Y-%m-%d %H:%M:%S') + " UTC"
                else:
                    temp_package['date_shipped'] = "Not shipped."

                if package['date_arrived'] != "NA":
                    temp_package['date_arrived'] = datetime.datetime.utcfromtimestamp(package['date_arrived']).strftime(
                        '%Y-%m-%d %H:%M:%S') + " UTC"
                else:
                    temp_package['date_arrived'] = "Not arrived."
                if package['status'] is not 'A':
                    num_of_packages += 1
                if 'node_master' in package:
                    temp_package['node_master'] = client.users_info(user=package['node_master'])['user']['real_name']
                packages.append(temp_package)

    else:
        return "User not in database."
    if isNode_Master:
        for user in database:
            for package in database[user]:
                temp_package = package.copy()
                if 'type' in package.keys() and not package['type'] == 'receiver':
                    break
                elif 'type' not in package.keys():
                    if package['node_master'] != session['id']:
                        continue
                    if package['date_shipped'] != "NS":
                        temp_package['date_shipped'] = datetime.datetime.utcfromtimestamp(
                            package['date_shipped']).strftime(
                            '%Y-%m-%d %H:%M:%S') + " UTC"
                    else:
                        temp_package['date_shipped'] = "Not shipped."

                    if package['date_arrived'] != "NA":
                        temp_package['date_arrived'] = datetime.datetime.utcfromtimestamp(
                            package['date_arrived']).strftime(
                            '%Y-%m-%d %H:%M:%S') + " UTC"
                    else:
                        temp_package['date_arrived'] = "Not arrived."
                    temp_package['recipient'] = client.users_info(user=user)['user']['real_name']
                    if package['status'] is not 'A':
                        num_of_packages += 1
                    packages.append(temp_package)
        return render_template("node_master.html", packages=packages, name=user_name, len=num_of_packages)
    else:
        return render_template("statuslist.html", packages=packages, name=user_name, len=num_of_packages)


@app.route('/logout')
def logout():
    del session['id']
    del session['name']
    return index()


@app.route('/confirm')
def confirm_package():
    if 'id' in session:
        package_id = int(request.args['package'])
        package = find_package(package_id, user=session['id'])
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'A'
            package['date_arrived'] = int(time.time())
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/deconfirm')
def deconfirm_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id, user=session['id'])
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'S'
            package['date_arrived'] = 'NA'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/delete')
def delete_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        user_id = find_package_owner(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'NAP':
            database[user_id].remove(package)
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/approve')
def approve_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'PAP':
            package['status'] = 'NS'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/deapprove')
def deapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'NS':
            package['status'] = 'PAP'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/disapprove')
def disapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'PAP':
            package['status'] = 'NAP'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/dedisapprove')
def dedisapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'NAP':
            package['status'] = 'PAP'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/ship')
def ship_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'NS':
            package['status'] = 'S'
            package['date_shipped'] = int(time.time())
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/deship')
def deship_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'NS'
            package['date_shipped'] = 'NS'
            with open('database.json', 'w') as outfile:
                json.dump(database, outfile)
        return user()
    return index()


@app.route('/update_contents')
def update_contents():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        for arg in request.args:
            if 'contents' in arg:
                package_id = int(arg[8:])
        package = find_package(package_id)
        package['contents'] = request.args['contents' + str(package_id)]
        with open('database.json', 'w') as outfile:
            json.dump(database, outfile)
        return user()
    return index()


@app.route('/update_note')
def update_note():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        for arg in request.args:
            if 'note' in arg:
                package_id = int(arg[4:])
        package = find_package(package_id)
        package['note'] = request.args['note' + str(package_id)]
        with open('database.json', 'w') as outfile:
            json.dump(database, outfile)
        return user()
    return index()


def find_package(id, user=None):
    if user == None:
        for user in database:
            for package in database[user]:
                if 'package' in package and package['package'] == id:
                    return package
    else:
        assert user in database
        for package in database[user]:
            if 'package' in package and package['package'] == id:
                return package
    return -1


def find_package_owner(id):
    for user in database:
        for package in database[user]:
            if 'package' in package and package['package'] == id:
                return user
    return -1

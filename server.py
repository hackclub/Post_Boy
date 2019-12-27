import requests
import os
import json
import slack
import yaml
import datetime
from bs4 import BeautifulSoup
import time

from flask import Flask, request, render_template, send_from_directory, session, flash, redirect
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired


class updaterForm(FlaskForm):
    labels = SelectMultipleField(u'Programming Language',
                                 choices=[
                                     ('Stickers', 'Stickers'),
                                     ('Minecraft', 'Minecraft'),
                                     ('Grant', 'Grant')
                                 ]
                                 )
    note = TextAreaField('Note')
    contents = TextAreaField('Contents')
    recipient = StringField('Recipient')
    tracking = StringField('tracking')
    img = StringField('picture')
    address = StringField('address')
    submit = SubmitField('Submit')


class recipientForm(FlaskForm):
    address = StringField('address')
    submit = SubmitField('Submit')


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

with open('states.json') as json_file:
    states = json.load(json_file)


@app.route("/")
def index():
    if 'id' not in session:
        return render_template("index.html")
    else:
        return redirect("/user")


@app.route('/img/<path>')
def send_assets(path):
    return send_from_directory('img', path)


@app.route('/<path>')
def send_style(path):
    return send_from_directory('static', path)


@app.route('/js/<path>')
def send_js(path):
    return send_from_directory('js', path)


def sort_by_date_ordered(package):
    return package['date_ordered']


def move_completed_packages_down(packages: list):
    for package in packages:
        if package['status'] == 'A' or package['status'] == 'NAP':
            packages.remove(package)
            packages.append(package)

def save_db():
    with open('database.json','w') as outfile:
        json.dump(database, outfile)

def save_state():
    with open('states.json','w') as outfile:
        json.dump(states, outfile)

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
        print(type(user_slack_id))
        if session['id'] not in database:
            database[session['id']] = [{"type": "receiver"}]
            save_db()
    else:
        user_slack_id = session['id']
        user_name = session['name']
    form = updaterForm()
    packages = []
    num_of_packages = 0
    isNode_Master = False
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
                if 'node_master' in package and package['node_master'] != '':
                    temp_package['node_master'] = getNameFromId(package['node_master'])
                packages.append(temp_package)
        packages.sort(key=sort_by_date_ordered)
        move_completed_packages_down(packages)
        for package in packages:
            package['date_ordered'] = datetime.datetime.utcfromtimestamp(
                package['date_ordered']).strftime(
                '%Y-%m-%d %H:%M:%S') + " UTC"
    else:
        if session['id'] not in database:
            database[session['id']] = [{"type": "receiver"}]
            save_db()
    if isNode_Master:
        for user in database:
            for package in database[user]:
                temp_package = package.copy()
                if 'type' not in package.keys() and (
                        package['node_master'] == session['id'] or 'node_master' not in package or package[
                    'node_master'] == ''):
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

                    if package['recipient']['id'] == session['id']:
                        temp_package['recipient'] = "Draft Package"
                    else:
                        temp_package['recipient'] = getNameFromId(user)
                    if package['status'] is not 'A':
                        num_of_packages += 1
                    packages.append(temp_package)

        packages.sort(key=sort_by_date_ordered)
        move_completed_packages_down(packages)
        for package in packages:
            package['date_ordered'] = datetime.datetime.utcfromtimestamp(
                package['date_ordered']).strftime(
                '%Y-%m-%d %H:%M:%S') + " UTC"
        return render_template("node_master.html", packages=packages, name=user_name, len=num_of_packages, form=form)
    else:
        return render_template("statuslist.html", packages=packages, name=user_name, len=num_of_packages, form=form)


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
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'A'
            package['date_arrived'] = int(time.time())
            save_db()
        return redirect("/user")
    return index()


@app.route('/deconfirm')
def deconfirm_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id, user=session['id'])
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'S'
            package['date_arrived'] = 'NA'
            save_db()
        return redirect("/user")
    return index()


@app.route('/delete')
def delete_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        user_id = package['recipient']['id']
        if 'package' in package and package['package'] == package_id and package['status'] == 'NAP':
            database[user_id].remove(package)
            save_db()
        return redirect("/user")
    return index()


@app.route('/approve')
def approve_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'PAP' and \
                package['recipient']['id'] != session['id']:
            package['status'] = 'NS'
            package['node_master'] = session['id']
            save_db()
        return redirect("/user")
    return index()


@app.route('/deapprove')
def deapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'NS':
            package['status'] = 'PAP'
            package['node_master'] = ''
            save_db()
        return redirect("/user")
    return index()


@app.route('/disapprove')
def disapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'PAP':
            package['status'] = 'NAP'
            package['node_master'] = session['id']
            save_db()
        return redirect("/user")
    return index()


@app.route('/dedisapprove')
def dedisapprove_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'NAP':
            package['status'] = 'PAP'
            package['node_master'] = ''
            save_db()
        return redirect("/user")
    return index()


@app.route('/ship')
def ship_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'NS':
            package['status'] = 'S'
            package['date_shipped'] = int(time.time())
            save_db()
        return redirect("/user")
    return index()


@app.route('/deship')
def deship_package():
    if 'id' in session and database[session['id']][0]['type'] == "node_master":
        package_id = int(request.args['package'])
        package = find_package(package_id)
        if package == -1:
            return redirect("/user")
        if 'package' in package and package['package'] == package_id and package['status'] == 'S':
            package['status'] = 'NS'
            package['date_shipped'] = 'NS'
            save_db()
        return redirect("/user")
    return index()


@app.route('/new')
def create_package():
    if 'id' in session:
        if isNodeMaster(session['id']):
            new_package = {
                "package": states['last_package_id'] + 1,
                "labels": [],
                "date_ordered": int(time.time()),
                "date_shipped": "NS",
                "date_arrived": "NA",
                "contents": "",
                "img": "",
                "address": "",
                "status": "PAP",
                "node_master": session['id'],
                "tracking_num": "-1",
                "note": "",
                "recipient": {
                    "name": session['name'],
                    "id": session['id']
                }
            }
        else:
            new_package = states['templates'][request.args['type']]
            new_package['package'] = states['last_package_id'] + 1
            new_package["date_ordered"] = int(time.time())
            new_package['recipient']['id'] = session['id']
            new_package['recipient']['name'] = session['name']

        database[session['id']].append(new_package)
        states['last_package_id'] += 1
        save_state()
        save_db()
        return redirect("/edit?package=" + str(states['last_package_id']) + "&new=true")


@app.route('/edit', methods=['GET', 'POST'])
def update_contents():
    if 'id' in session:
        package_id = int(request.args['package'])
        is_new_package = 'new' in request.args and request.args['new'] == 'true'
        package = find_package(package_id)
        temp_package = package.copy()
        recipient_id = package['recipient']['id']
        if 'cancel' in request.args and request.args['cancel'] == 'true':
            if 'new' in request.args and request.args['new'] == 'True':
                database[recipient_id].remove(package)
                save_db()
            return redirect("/user")
        temp_package['recipient'] = {'name': getNameFromId(recipient_id),
                                     'id': recipient_id}
        if database[session['id']][0]['type'] == "node_master":
            form = updaterForm()
            if form.validate_on_submit():
                if form.recipient.data != recipient_id:
                    temp_package['contents'] = form.contents.data
                    temp_package['note'] = form.note.data
                    temp_package['tracking_num'] = int(form.tracking.data)
                    temp_package['labels'] = form.labels.data
                    temp_package['img'] = form.img.data
                    temp_package['address'] = form.address.data
                    temp_package['recipient']['id'] = form.recipient.data
                    temp_package['recipient']['name'] = getNameFromId(form.recipient.data)
                    if form.recipient.data in database:
                        database[form.recipient.data].append(temp_package)
                    else:
                        database[form.recipient.data] = [{"type": "receiver"}, temp_package]
                    database[recipient_id].remove(package)
                else:
                    package['contents'] = form.contents.data
                    package['note'] = form.note.data
                    package['tracking_num'] = int(form.tracking.data)
                    package['address'] = form.address.data
                    package['labels'] = form.labels.data
                    package['img'] = form.img.data
                save_db()
                return redirect('/user')
            else:
                form = updaterForm(
                    recipient=u'' + temp_package['recipient']['id'],
                    contents=u'' + temp_package['contents'],
                    note=u'' + temp_package['note'],
                    tracking=u'' + str(temp_package['tracking_num']),
                    address=u'' + str(temp_package['address']),
                    img=u'' + temp_package['img']
                )
            return render_template("master_edit.html", package=temp_package, name=session['name'], form=form,
                                   is_new_package=is_new_package)
        else:
            if package['recipient']['id'] == session['id']:
                form = recipientForm()
                can_edit = package['status'] == 'NS' or package['status'] == 'PAP'
                print(package['status'])
                if form.validate_on_submit():
                    if can_edit:
                        package['address'] = form.address.data
                        save_db()
                        return redirect('/user')
                else:
                    form = updaterForm(
                        recipient=u'' + temp_package['recipient']['id'],
                        contents=u'' + temp_package['contents'],
                        note=u'' + temp_package['note'],
                        tracking=u'' + str(temp_package['tracking_num']),
                        address=u'' + str(temp_package['address']),
                        img=u'' + temp_package['img']
                    )
                return render_template("recipient_edit.html", package=temp_package, name=session['name'], form=form,
                                       can_edit=can_edit)
            else:
                return redirect("/user")
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


def isNodeMaster(id):
    return database[id][0]['type'] == 'node_master'


def getNameFromId(id):
    client = slack.WebClient(token=auth_token)
    return client.users_info(user=id)['user']['real_name']

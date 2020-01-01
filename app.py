import requests
import os
import json
import slack
import datetime
from bs4 import BeautifulSoup
import time
import tools.airtable as airtable
from flask import Flask, request, render_template, send_from_directory, session, flash, redirect
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired
from os import environ


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
    note = StringField('note')
    submit = SubmitField('Submit')


app = Flask(__name__)
if __name__ == '__main__':
    app.run(debug=True)

app.secret_key = '\xf0"b1\x04\xe0.[?w\x0c(\x94\xcdh\xc1yq\xe3\xaf\xf2\x8f^\xdc'

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

auth_token = os.getenv('AUTH_TOKEN')
airtable_key = os.getenv('AIRTABLE_KEY')


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

def convertLabelNameToArray(label:str):
    label_array = []
    if 'sticker' in label.lower():
        # Append sticker label
        label_array.append(("Sticker", "Sticker"))
        if 'box' in label.lower():
            label_array.append(("Box", "Box"))
            # Append size label
            label_array.append((label.replace("Sticker Box", ""), label.replace("Sticker Box", "")))
        else:
            label_array.append(("Envelope", "Envelope"))
    else:
        if 'minecraft' in label.lower():
            label_array.append(("Envelope", "Envelope"))
        else:
            label_array.append((label, label.replace(" ", "-")))
    return label_array

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    isNew = 'new' in request.args and request.args['new'] == 'true'
    if isNew:
        type = request.args['type'] if 'type' in request.args else ''
        scenario = airtable.getMailScenario(type, slack_id=session['id'])
        scenario['date_ordered'] = datetime.date.today().strftime("%b. %d, %Y")
        scenario['status'] = 'PAP'
        scenario['labels'] = convertLabelNameToArray(scenario['labels'])
        form = recipientForm()
        if form.validate_on_submit():
                note = form.note.data
                observer = slack.WebClient(token=auth_token)
                observer.chat_postMessage(
                    channel="GNTFDNEF8",
                    text="<@UNRAW3K7F> test " + type + " <@" + session['id'] + "> " + note
                )
                return redirect('/user')
        return render_template("recipient_edit.html", package=scenario, name=session['name'], form=form)


def login(auth_code):
    # An empty string is a valid token for this request
    client = slack.WebClient(token="")
    # Request the auth tokens from Slack
    response = client.oauth_access(client_id=client_id, client_secret=client_secret, code=auth_code)

    user_client = slack.WebClient(token=response['access_token'])
    info = user_client.users_identity()
    # info = {'user':{'id':'UJ9864R4N', 'real_name':'Frank Hui'}}
    user_slack_id = info['user']['id']
    user_name = info['user']['name']
    session['id'] = user_slack_id
    session['name'] = user_name

@app.route('/user', methods=["GET", "POST"])
def user():
    if 'id' not in session:
        if 'code' not in request.args:
            return redirect("/")
        # Retrieve the auth code from the request params
        auth_code = request.args['code']
        login(auth_code)
    packages = []
    num_of_packages = 0
    is_nm = airtable.is_node_master(session['id'])
    packages = airtable.getPackages(session['id'])
    packages.sort(key=sort_by_date_ordered)
    move_completed_packages_down(packages)
    for package in packages:
        package['node_master'] = getNameFromId(package['node_master'])
        package['note'] = package['note'].replace("\n", "<br>")
        package['contents'] = package['contents'].replace("\n", "<br>")
        if package['status'] != 'A' and package['status'] != 'NAP':
            num_of_packages += 1
        package['labels'] = convertLabelNameToArray(package['labels'])
        package['date_ordered'] = datetime.datetime.strptime(package['date_ordered'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime(
            "%b. %d, %Y")

    return render_template("statuslist.html", packages=packages, name=session['name'], len=num_of_packages)


@app.route('/logout')
def logout():
    del session['id']
    del session['name']
    return redirect("/")


def getNameFromId(id):
    observer = slack.WebClient(token=auth_token)
    try:
        return observer.users_info(user=id)['user']['real_name']
    except:
        return "No Node Master found."

import requests
import os
import json
import slack
import datetime
from bs4 import BeautifulSoup
import time
if os.path.exists("secrets.json"):
    with open("secrets.json") as f:
        secrets = json.load(f)

    for key in secrets.keys():
        os.environ[key] = secrets[key]
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

app.secret_key = os.getenv('APP_SECRET_KEY')

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

auth_token = os.getenv('AUTH_TOKEN')
airtable_key = os.getenv('AIRTABLE_KEY')


@app.route("/")
def index():
    if 'id' not in session:
        if 'theme' not in session:
            return render_template("index.html", dark='day')
        else:
            return render_template("index.html", dark=session['theme'])
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


def convertLabelNameToArray(label: str):
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
    checkSession()
    isNew = 'new' in request.args and request.args['new'] == 'true'
    if isNew:
        if not airtable.isLeader(session['id']) and not airtable.is_node_master(session['id']):
            return redirect('/user')
        type = request.args['type'] if 'type' in request.args else ''
        scenario = airtable.getMailScenario(type, slack_id=session['id'])
        scenario['date_ordered'] = datetime.date.today().strftime("%b. %d, %Y")
        scenario['status'] = 'PAP'
        scenario['type'] = scenario['labels']
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
        return render_template("recipient_edit.html", package=scenario, name=session['name'], form=form, dark=session['theme'])


def login(auth_code):
    # An empty string is a valid token for this request
    client = slack.WebClient(token="")
    # Request the auth tokens from Slack
    try:
        response = client.oauth_access(client_id=client_id, client_secret=client_secret, code=auth_code)
    except Exception as e:
        return str(e)
    user_client = slack.WebClient(token=response['access_token'])
    info = user_client.users_identity()
    # info = {'user':{'id':'UJ9864R4N', 'real_name':'Frank Hui'}}
    user_slack_id = info['user']['id']
    user_name = info['user']['name']
    session['id'] = user_slack_id
    session['name'] = user_name
    return 0


@app.route('/user', methods=["GET", "POST"])
def user():
    if 'code' in request.args:
        if 'id' in session:
            return redirect('/user')
        else:
            auth_code = request.args['code']
            error = login(auth_code)
            if error != 0:
                return render_template("error.html", error=error)
            else:
                return redirect('/user')
    num_of_packages = 0
    type = ''
    if airtable.is_node_master(session['id']):
        type = 'Node Master'
    elif airtable.isLeader(session['id']):
        type = 'Club Leader'
    packages = airtable.getPackages(session['id'])
    packages.sort(key=sort_by_date_ordered)
    move_completed_packages_down(packages)
    for package in packages:
        package['node_master'] = getNameFromId(package['node_master'])
        package['contents'] = package['contents'].replace("\n", "<br>")
        if package['status'] != 'A' and package['status'] != 'NAP':
            num_of_packages += 1
        package['labels'] = convertLabelNameToArray(package['labels'])
        package['date_ordered'] = convertToDateString(package['date_ordered'])
        package['date_shipped'] = '' if package['date_shipped'] == '' else convertToDateString(package['date_shipped'])
        package['date_arrived'] = '' if package['date_arrived'] == '' else convertToDateString(package['date_arrived'])
    checkSession()
    return render_template("statuslist.html", packages=packages, name=session['name'], len=num_of_packages, type=type, dark=session['theme'])


def convertToDateString(date):
    return datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ').strftime(
        "%b. %d, %Y")


@app.route('/logout')
def logout():
    if 'id' in session: del session['id']
    if 'name' in session: del session['name']
    if 'theme' in session: del session['theme']
    return redirect("/")


def getNameFromId(id):
    observer = slack.WebClient(token=auth_token)
    try:
        return observer.users_info(user=id)['user']['real_name']
    except:
        return "No Node Master found."

@app.route("/theme", methods=['POST'])
def setTheme():
    session['theme'] = request.get_data().decode("utf-8")
    return "200"

def checkSession():
    if 'theme' not in session: session['theme'] = 'day'
    if 'id' not in session: return -1
    if 'name' not in session: return -1

if __name__ == '__main__':
    app.run(debug=True)
import requests
import os
import json
import yaml

from bs4 import BeautifulSoup

from flask import Flask, request, render_template, send_from_directory
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/user')
def search_books():
    auth = request.args.get('code')
    if not auth:
        return render_template("statuslist.html", links=[], error="Not signed in.")

    if not os.path.isdir("books"):
        print("No books directory found. Exiting...")
        return
    directory = os.fsencode("books")
    possible_files = {}
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".json"):
            with open("books/" + filename) as json_file:
                data = json.load(json_file)
                text = data['text']
                if keyword in text:
                    index = text.find(keyword)
                    possible_files[text[index:index + 20] + "..."] = filename[0:filename.find(".json")]
        else:
            continue
    print(possible_files)
    if not possible_files:
        return render_template("book_results.html", links=[], error="No results found.")

    return render_template("book_results.html", links=possible_files.items(), error="")
# Post_Boy
GUI to track shipments from Hack Club

## Setting up a development environment
Dependencies:
  - Install Heroku: [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
1. Clone repo: `git clone https://github.com/hackclub/Post_Boy.git`
2. Enter repo: `cd Post_Boy`
3. Set up virtual environment: `python3 -m venv venv`
4. Activate venv: `source venv/bin/activate`
5. Install requirements: `pip install -r requirements.txt`
6. Create an export file with needed credentials:
```
export.sh

export CLIENT_ID="1234.1234"
export CLIENT_SECRET=abcd
export AUTH_TOKEN=xoxp-1234
export AIRTABLE_KEY=keyABCD
```
7. Export variables: `source export.sh`
8. Run heroku environment: `heroku local`

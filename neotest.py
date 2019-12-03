#!/usr/bin/python

from neo4j import GraphDatabase
import datetime
import sys
from mailchimp3 import MailChimp
import json

def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results


client = MailChimp(mc_api='98408af2ecb507cdd3ff9e5d173a6b72-us20', mc_user='fjblau@gmail.com')

def getEmailsFromCampaign(id):
	campaignData = json.loads(json.dumps(client.reports.get(campaign_id=id, get_all=False)))
	listData = json.loads(json.dumps(client.lists.members.all(list_id=campaignData["list_id"])))
	return extract_values(listData,"email_address")

print (getEmailsFromCampaign('6032f808ac'))

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "2Ellbelt!"))



def ts_to_str(ts):
	return datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')

#def docs_downloaded_by(tx, name):
#    for record in tx.run( "MATCH  (p:Person {firstname: {name}})-[:DOWNLOAD_FROM_EMAIL] -> (d)"
#						  "RETURN p.firstname, d.docName, d.createdAt", name=name):
#    	print(str(record["p.firstname"]), str(record["d.docName"]), ts_to_str(record["d.createdAt"]))

#with driver.session() as session:
#    session.read_transaction(docs_downloaded_by, sys.argv[1])


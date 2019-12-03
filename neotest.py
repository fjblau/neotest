#!/usr/bin/python

from neo4j import GraphDatabase
import datetime
import sys

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "2Ellbelt!"))

def ts_to_str(ts):
	return datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')

def docs_downloaded_by(tx, name):
    for record in tx.run( "MATCH  (p:Person {firstname: {name}})-[:DOWNLOAD_FROM_EMAIL] -> (d)"
						  "RETURN p.firstname, d.docName, d.createdAt", name=name):
    	print(str(record["p.firstname"]), str(record["d.docName"]), ts_to_str(record["d.createdAt"]))

with driver.session() as session:
    session.read_transaction(docs_downloaded_by, sys.argv[1])


#!/usr/local/opt/python/libexec/bin/python

from neo4j import GraphDatabase
import datetime
import sys
import json
import mysql.connector
import os


	
mydb = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  user=os.environ["MYSQL_USER"],
  passwd=os.environ["MYSQL_PASSWD"],
  database=os.environ["MYSQL_DATABASE"]
)

mycursor = mydb.cursor()

mycursor.execute("SELECT * FROM opportunities")

myresult = mycursor.fetchall()

for x in myresult:
  print(x)

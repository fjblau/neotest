#!/usr/local/opt/python/libexec/bin/python

from neo4j import GraphDatabase
import datetime
import sys
import json
import mysql.connector

mydb = mysql.connector.connect(
  host="159.69.115.170",
  user="root",
  passwd="2Ellbelt!",
  database="ga_tracking"
)

mycursor = mydb.cursor()

mycursor.execute("SELECT * FROM accounts")

myresult = mycursor.fetchall()

for x in myresult:
  print(x)

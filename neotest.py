#!/usr/local/opt/python/libexec/bin/python

from neo4j import GraphDatabase
import datetime
import sys
from mailchimp3 import MailChimp
import json


#client = MailChimp(mc_api='98408af2ecb507cdd3ff9e5d173a6b72-us20', mc_user='fjblau@gmail.com')
#client = MailChimp(mc_api= sys.argv[1], mc_user='fjblau@gmail.com')
client = MailChimp(mc_api= sys.argv[1], mc_user='accountadmin@massiveart.com')

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "2Ellbelt!"))

def ts_to_str(ts):
    return datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')

def sq(q):
	return "'" + q + "'"

def getAllLists():
    listData = json.loads(json.dumps(client.lists.all(get_all=True)))
    for listRec in listData["lists"]:
        listId = listRec["id"]
        listName = sq(listRec["name"])
        marketing_permissions = sq(str(listRec["marketing_permissions"]))
        listMembers = json.loads(json.dumps(client.lists.members.all(list_id=listId, get_all=True)))
        listId = sq(listRec["id"])
        for email in listMembers["members"]:
        	emailAddress = sq(email["email_address"])
        	memberId = sq(email["id"])
        	createText = """
        	MERGE (l:List{listId:"""+listId+", listName:"+listName+"""})
        	MERGE (p:Person{emailAddress:"""+emailAddress+", memberId:"+memberId+", marketing_permissions:"+marketing_permissions+"""})
        	MERGE (p) -[r:MEMBER_OF_LIST]-> (l)
        	ON CREATE SET p.CreatedAt = timestamp()
        	"""
        	#print(createText)
        	with driver.session() as session:
        		result = session.run(createText)
        		print(result)
        	#memberActivities = json.loads(json.dumps(client.lists.members.activity.all(list_id=listRec["id"], subscriber_hash=email["id"])))
        	#print(memberActivities)
            

def getAllCampaigns():
    campaignData = json.loads(json.dumps(client.campaigns.all(get_all=True)))
    for campaign in campaignData["campaigns"]:
        campaignId = sq(campaign["id"])
        campaignName = sq(campaign["settings"]["title"].replace("'",""))
        campaignRecipientListId = sq(campaign["recipients"]["list_id"])
        createText = """
        	MERGE (c:Campaign{campaignId:"""+campaignId+", name:"+campaignName+"""})
            MERGE (l:List{listId:"""+campaignRecipientListId+"""})
            MERGE (l) -[r:LIST_USED_IN]-> (c)
            ON CREATE SET c.CreatedAt = timestamp()
            """
        #print(createText)
        with driver.session() as session:
           result = session.run(createText)
           print(result)

getAllLists()
getAllCampaigns()





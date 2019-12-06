#!/usr/bin/python

from neo4j import GraphDatabase
import datetime
import sys
from mailchimp3 import MailChimp
import json
import requests


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
            domain = sq(email["email_address"].split('@')[1])
            memberId = sq(email["id"])
            createText = """
            MERGE (l:List{listId:"""+listId+", listName:"+listName+"""})
            MERGE (p:Person{emailAddress:"""+emailAddress+", memberId:"+memberId+", marketing_permissions:"+marketing_permissions+"""})
            MERGE (d:Domain{domain:"""+domain+"""})
            MERGE (p) -[r:MEMBER_OF_LIST]-> (l)
            MERGE (p) -[r2:AT_DOMAIN]-> (d)
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
        campaignStatus = campaign["status"]
        print(campaign["status"])
        emailsSent= campaign["emails_sent"]
        campaignName = sq(campaign["settings"]["title"].replace("'",""))
        campaignRecipientListId = sq(campaign["recipients"]["list_id"])
        createText = """
        MERGE (c:Campaign{campaignId:"""+campaignId+", name:"+campaignName+",emails_sent:"+str(emailsSent)+"""})
        MERGE (l:List{listId:"""+campaignRecipientListId+"""})
        MERGE (l) -[r:LIST_USED_IN]-> (c)
        ON CREATE SET c.CreatedAt = timestamp()
        """
    #print(createText)
        with driver.session() as session:
            result = session.run(createText)
            print(result)

        if (campaignStatus == 'sent'):
            print("Sent Status")
            createText = """
            MATCH (c:Campaign{campaignId:"""+campaignId+"""})
            MATCH (l:List{listId:"""+campaignRecipientListId+"""})
            MERGE (c) - [:SENT_FROM] - (e:Email {content:'Email'}) - [r:SENT_TO] - (l)
            """
            with driver.session() as session:
                result = session.run(createText)
                print(result)

        #print(json.loads(json.dumps(client.reports.email_activity.all(campaign_id=campaignId, get_all=True))))
        emailActivity = json.loads(json.dumps(client.reports.email_activity.all(campaign_id=campaign["id"], get_all=False)))
        for email in emailActivity["emails"]:
            emailId = sq(email["email_id"])
            emailAddress = sq(email["email_address"])
            #createText = """
            #MATCH (p:Person{emailAddress:"""+emailAddress+""""}),
            #      (c2:Campaign {campaignId:"""+campaignId+"""}),
            #      (l2:List{listId:"""+campaignRecipientListId+"""})
            #MERGE (e:Email) - [to:SENT_TO] -> (p) -> [from:SENT_FROM] - (l2)
            """

            #for activity in email["activity"]:
            #    createText = """
            #    MATCH (p:Person{emailAddress:"""+emailAddress+""""}),
            #    MERGE (e:Email) - [ec:SENT_TO] -> (p)
            #    """
        

#getAllLists()
getAllCampaigns()





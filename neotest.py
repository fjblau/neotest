#!/usr/local/opt/python/libexec/bin/python

from neo4j import GraphDatabase
import datetime
import sys
from mailchimp3 import MailChimp
import json
import requests
import hashlib
import maya

with open('persona.json', 'r') as personafile:
    personadata = json.load(personafile)

client = MailChimp(mc_api= sys.argv[1], mc_user='accountadmin@massiveart.com')

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "2Ellbelt!"))

def deltaSeconds(action, sent):
    minutes = int((maya.parse(action) - maya.parse(sent)).seconds/60)
    if (minutes < 5):
        response = "Fast"
    elif (minutes < 60):
        response = "Medium"
    elif (minutes < 1440):
        response = "Slow"
    else:
        response ="Very Slow"
    return response


def ts_to_str(ts):
    return datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')

def sq(q):
    return "'" + q + "'"

def hashemailId(c, l, e):
    hashed = c+l+e
    return hashlib.sha256(hashed.encode()).hexdigest()

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
            MERGE (p:Person{emailAddress:"""+emailAddress+", memberId:"+memberId+"""})
            MERGE (d:Domain{domain:"""+domain+"""})
            MERGE (p) -[r:MEMBER_OF_LIST]-> (l)
            MERGE (p) -[r2:AT_DOMAIN]-> (d)
            ON CREATE SET p.CreatedAt = timestamp()
            """
        #print(createText)
            with driver.session() as session:
                result = session.run(createText)
                print("Lists", result)
        #memberActivities = json.loads(json.dumps(client.lists.members.activity.all(list_id=listRec["id"], subscriber_hash=email["id"])))
        #print(memberActivities)


def getAllCampaigns():
    campaignData = json.loads(json.dumps(client.campaigns.all(get_all=True)))
    for campaign in campaignData["campaigns"]:

        campaignId = sq(campaign["id"])
        #print(personadata["campaignId"])
        #if (campaign["id"] == personadata["campaignId"]):
        campaignSendTime = campaign["send_time"]
        campaignStatus = campaign["status"]
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
            #print(result)

        if (campaignStatus == 'sent'):
            
            createText = """
            MATCH (c:Campaign{campaignId:"""+campaignId+"""})
            MATCH (l:List{listId:"""+campaignRecipientListId+"""})
            MERGE (e:EmailGenerated{content:'Email Template'}) - [:GENERATED_BY] -> (c) 
            MERGE (e2:EmailGenerated {content:'Email Template'}) - [r:SENT_TO] -> (l)
            """
            with driver.session() as session:
                result = session.run(createText)
                #print(result)

        emailActivity = json.loads(json.dumps(client.reports.email_activity.all(campaign_id=campaign["id"], get_all=False)))
        for email in emailActivity["emails"]:
            emailHashId = hashemailId(campaign["id"], campaign["recipients"]["list_id"], email["email_address"])
            emailId = sq(email["email_id"])
            emailAddress = sq(email["email_address"])

            createText = """
            MATCH (p:Person{emailAddress:"""+emailAddress+"""}),
                  (c2:Campaign {campaignId:"""+campaignId+"""}),
                  (l2:List{listId:"""+campaignRecipientListId+"""})
            MERGE (e:Email {content:'Email', status: 'Sent', emailHashId:"""+sq(emailHashId)+"""}) - [to:SENT_TO] -> (p)
            MERGE (e2:Email{content:'Email', status: 'Sent', emailHashId:"""+sq(emailHashId)+"""}) - [from:SENT_FROM] -> (l2)
            """
            with driver.session() as session:
                result = session.run(createText)
                #print(result)
            
            if "activity" in email:
                for emailAction in email["activity"]:
                    timeBeforeRead = deltaSeconds(emailAction["timestamp"], campaignSendTime)
                    if emailAction["action"] == 'open':
                        createText= """
                                    MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                    MATCH (c:Campaign{campaignId:"""+campaignId+"""})
                                    MERGE (p) - [:OPENED {timestamp:"""+sq(emailAction["timestamp"])+"""}] -> (c)
                                    MERGE (ps:Persona {persona:"Engagement"})
                                    MERGE (p) - [rp:HAS_PERSONA {source:"Open", fromCampaign:"""+campaignId+""", points: 1}] -> (ps)
                                    SET rp.responseTime ="""+sq(timeBeforeRead)+"""
                                    """
                    elif emailAction["action"] == 'bounce':
                        createText="""
                                    MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                    MATCH (c:Campaign{campaignId:"""+campaignId+"""})
                                    MERGE (p) - [:BOUNCED {timestamp:"""+sq(emailAction["timestamp"])+"""}] -> (c)
                                    """
                    elif emailAction["action"] == 'click':
                        for link in personadata["links"]:
                            if (json.dumps(emailAction["url"]) == json.dumps(link["linkURL"])):
                                for personaScore in link["personas"]:
                                    createText= """
                                             MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                             MERGE (ps:Persona {persona:"""+sq(personaScore["persona"])+"""})
                                             MERGE (p) - [rp1:HAS_PERSONA {source:"Click", fromCampaign:"""+campaignId+", points:"+str(personaScore["clickPoints"])+"""}] -> (ps)
                                             SET rp1.responseTime ="""+sq(timeBeforeRead)+"""
                                             MERGE (per:Persona {persona:"Engagement"})
                                             MERGE (p) - [rp:HAS_PERSONA {source:"Click", fromCampaign:"""+campaignId+", points:"+str(personaScore["openPoints"])+"""}] -> (per)
                                             SET rp.responseTime ="""+sq(timeBeforeRead)+"""
                                             """
                                    with driver.session() as session:
                                        result = session.run(createText)


                                    #print(personaScore["persona"], personaScore["clickPoints"])
                        createText= """
                                    MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                    MERGE (u2:URL {url:"""+sq(emailAction["url"])+"""})
                                    MERGE (p) - [:CLICKED {timestamp:"""+sq(emailAction["timestamp"])+"""}] -> (u2)
                                    """
                    #print(createText)
                    with driver.session() as session:
                        result = session.run(createText)
                        #print(result)
getAllLists()
getAllCampaigns()





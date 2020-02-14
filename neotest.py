#!/usr/bin/env python

from neo4j import GraphDatabase
import datetime
import sys
from mailchimp3 import MailChimp
import json
import hashlib
import maya
import mysql.connector
import os
from furl import furl

with open('persona.json', 'r') as personafile:
    personadata = json.load(personafile)

client = MailChimp(mc_api= sys.argv[1], mc_user='accountadmin@massiveart.com')

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "2Ellbelt!"), encrypted=False)

def checkCRM(emailAddress):
    mydb = mysql.connector.connect(
    host=os.environ["MYSQL_HOST"],
    user=os.environ["MYSQL_USER"],
        passwd=os.environ["MYSQL_PASSWD"],
      database=os.environ["MYSQL_DATABASE"]
    )
    mycursor = mydb.cursor()
    query = """
            SELECT email_address, confirm_opt_in
            FROM email_addresses
            WHERE email_address = """+sq(emailAddress)
    mycursor.execute(query)
    return mycursor.fetchall()

def loadCustomers():
    mydb = mysql.connector.connect(
    host=os.environ["MYSQL_HOST_EASYBILL"],
    user=os.environ["MYSQL_USER_EASYBILL"],
        passwd=os.environ["MYSQL_PASSWD_EASYBILL"],
      database=os.environ["MYSQL_DATABASE_EASYBILL"]
    )
    mycursor = mydb.cursor()
    query = """
            SELECT DISTINCT LOWER(SUBSTRING(h.email, LOCATE('@', email) + 1)) as domain,
            sum(l.total_price_net) totalInvoices
            FROM easybill_headers h
            join easybill_lines l on h.document_id = l.header_id AND h.email is not null
             WHERE  LOWER(SUBSTRING(h.email, LOCATE('@', email) + 1)) != 'massiveart.com'
            GROUP BY LOWER(SUBSTRING(h.email, LOCATE('@', email) + 1))"""
    mycursor.execute(query)
    for domain, totalInvoices in mycursor:
        #print(domain, totalInvoices)
        createText = """
            MATCH (d3:Domain {domain:"massiveart.com"})
            MERGE (d:Domain{domain:"""+sq(domain)+"""})
            MERGE (d)-[:IS_CUSTOMER_OF]-(d3)
            SET d.totalInvoices = """+str(totalInvoices)
        with driver.session() as session:
            result = session.run(createText)
            print("Domains", result)

    return

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

def getCampaignId(webId):
    campaignData =  json.loads(json.dumps(client.campaigns.all(get_all=True)))
    for campaign in campaignData["campaigns"]:
        if str(campaign["web_id"]) == str(webId):
            return campaign["id"]
   

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
            with driver.session() as session:
                result = session.run(createText)
                print("Lists", result)

            for crmRec in (checkCRM(email["email_address"])):
                createText = """
                MERGE (p:Person{emailAddress:"""+emailAddress+", memberId:"+memberId+"""})
                MERGE (c:CRM{crm: 'SuiteCrm'})
                MERGE (p) -[r:IN_CRM {crm_opt_in:"""+sq(crmRec[1])+"""}]-> (c)
                ON CREATE SET r.CreatedAt = timestamp()
                """
                with driver.session() as session:
                    result = session.run(createText)


def getCampaign(webId):

    cId = getCampaignId(webId)
    campaign = client.campaigns.get(campaign_id=cId)
    campaignId = sq(campaign["id"])
    campaignSendTime = campaign["send_time"]
    campaignStatus = campaign["status"]
    emailsSent= campaign["emails_sent"]
    campaignName = sq(campaign["settings"]["title"].replace("'",""))
    campaignRecipientListId = sq(campaign["recipients"]["list_id"])
    createText = """
    MERGE (c:Campaign{campaignId:"""+campaignId+", name:"+campaignName+"""})
    MERGE (l:List{listId:"""+campaignRecipientListId+"""})
    MERGE (l) -[r:LIST_USED_IN]-> (c)
    SET c.emails_sent = """+str(emailsSent)+"""
    """
    with driver.session() as session:
        result = session.run(createText)

    emailActivity = json.loads(json.dumps(client.reports.email_activity.all(campaign_id=campaign["id"], get_all=True)))

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
        
        if "activity" in email:
            for emailAction in email["activity"]:
                timeBeforeRead = deltaSeconds(emailAction["timestamp"], campaignSendTime)
                if emailAction["action"] == 'open':
                    createText= """
                                MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                MATCH (c:Campaign{campaignId:"""+campaignId+"""})
                                MERGE (p) - [o:OPENED] -> (c)
                                ON CREATE SET o.timestamp = """+sq(emailAction["timestamp"])+""", o.openCount = 2
                                ON MATCH SET o.timestamp = """+sq(emailAction["timestamp"])+""", o.openCount = o.openCount + 1
                                """
                elif emailAction["action"] == 'bounce':
                    createText="""
                                MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                MATCH (c:Campaign{campaignId:"""+campaignId+"""})
                                MERGE (p) - [:BOUNCED {timestamp:"""+sq(emailAction["timestamp"])+"""}] -> (c)
                                """
                elif emailAction["action"] == 'click':
                    for link in personadata["links"]:
                        sourceLink = furl(json.dumps(emailAction["url"])).remove(args=True, fragment=True).url.strip('%22')
                        targetLink = furl(json.dumps(link["linkURL"])).remove(args=True, fragment=True).url.strip('%22')
                        if (sourceLink == targetLink):
                            for personaScore in link["personas"]:
                                createText= """
                                         MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                         MERGE (ps:Persona {persona:"""+sq(personaScore["persona"])+"""})
                                         MERGE (p) - [rp1:HAS_PERSONA {source:"Click", fromCampaign:"""+campaignId+"""}] -> (ps)
                                         ON CREATE SET rp1.responseTime ="""+sq(timeBeforeRead)+""", rp1.points = 2
                                         ON MATCH SET rp1.points = rp1.points + 1
                                         
                                         """
                                with driver.session() as session:
                                    result = session.run(createText)
                    createText= """
                                MATCH (p:Person{emailAddress:"""+emailAddress+"""})
                                MERGE (u2:URL {url:"""+sq(sourceLink)+"""})
                                MERGE (p) - [c:CLICKED] -> (u2)
                                ON CREATE SET c.timestamp = """+sq(emailAction["timestamp"])+""", c.clickCount = 2
                                ON MATCH SET c.timestamp = """+sq(emailAction["timestamp"])+""", c.clickCount = c.clickCount + 1
                                """
                with driver.session() as session:
                    result = session.run(createText)

#getAllLists()
#getCampaign('3175601')
loadCustomers()
#print(getCampaignId('3176125'))




import pandas as pd
import numpy as np
import requests
import json
import re
from slackclient import SlackClient
from collections import defaultdict

'''___________SETUP FUNCTIONS___________'''

def getconfigs(file):
    #extracts configs from JSON file
    configs = json.load(open(file))
    apitoken = configs.get("slackapitoken")
    url = configs.get("apinode")
    backup = configs.get("backupnodes")
    port=configs.get("port")
    blockinterval = configs.get("blockintervalnotification")
    minmissedblocks = configs.get("minmissedblocks")
    channelnames = configs.get("channels")
    usernames = configs.get("users")
    numdelegates = configs.get("numdelegates")
    blockrewards = configs.get("blockrewards")
    blockspermin = configs.get("blockspermin")
    return apitoken,url,backup,port,blockinterval,minmissedblocks,channelnames,usernames,numdelegates,blockrewards,b$

def cleanurl(url,port):
    cleanitems=['https://','http://','/',':'+port]
    for i in cleanitems:
        url=url.replace(i,'')
    return url

def getusernames(file):
    #gets username mappings from the JSON file
    usernames=json.load(open(file))
    return usernames

'''___________NODE API FUNCTIONS___________'''

def getdelegates(url):
    #gets current delegates from the url node api
    delegates = pd.DataFrame(requests.get(url+'api/delegates?orderBy=vote').json()['delegates'])
    delegates['vote']=pd.to_numeric(delegates['vote'])
    return delegates

def getpeers(url):
    #gets current peers from the url node api
    peers = pd.DataFrame(requests.get(url+'api/peers').json()['peers'])
    return peers

def getstatus(url,backup,tol=1):
    #gets current height from the list of backup nodes
    backupheights={}
    for i in backup:
        try:
            backupheights[i]=getheight(i)
        except:

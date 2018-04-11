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
    blockinterval = configs.get("missedblockinterval")
    minmissedblocks = configs.get("minmissedblocks")
    channelnames = configs.get("channels")
    usernames = configs.get("users")
    numdelegates = configs.get("numdelegates")
    blockrewards = configs.get("blockrewards")
    blockspermin = configs.get("blockspermin")
    return apitoken,url,blockinterval,minmissedblocks,channelnames,usernames,numdelegates,blockrewards,blockspermin

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

def getstatus(url,tol=1):
    #gets current status from the url node api
    peers=getpeers(url)
    height=getheight(url)
    total=len(peers)
    peers=peers[peers['state']==2]    #filters to connected peers
    connectedpeers=len(peers)
    peerheight=peers['height'].mode()[0]    #calculates the mode height from connected peers
    consensus=round(len(peers[abs(peers['height']-height)<=tol])/total*100,2) #calculates consensus from peer height
    return height,connectedpeers,peerheight,consensus

def getheight(url):
    #gets current block height from the url node api
    height = requests.get(url+'api/blocks/getHeight').json()['height']
    return height

'''___________SLACK API FUNCTIONS___________'''

def getchannellist(apitoken):
    #gets a list of all users in the slack team
    slack_client = SlackClient(apitoken)
    channellist=slack_client.api_call("channels.list",exclude_archived=1)['channels']
    return channellist

def getchannelids(channelnames,apitoken):
    #gets channelids for specified channels in a slack team
    channelids={}
    channelnames=[v.lower() for v in channelnames]
    channellist=getchannellist(apitoken)
    channellist=[v for v in channellist if str(v.get('name')).lower() in channelnames]
    for name in channelnames:
        id=None
        for channel in channellist:
            if str(channel.get('name')).lower() == name.lower():
                id=channel.get('id')
        channelids[name]=id
    return channelids

def getuserlist(apitoken):
    #gets a list of all users in the slack team
    slack_client = SlackClient(apitoken)
    userlist=slack_client.api_call("users.list")['members']
    return userlist

def getuserids(usernames,apitoken):
    #gets userids for specified usernames in a slack team userlist
    userids={}
    usernames=[v.lower() for v in usernames]
    userlist=getuserlist(apitoken)
    userlist=[v for v in userlist if (str(v.get('name')).lower() in usernames) or (str(v.get('real_name')).lower() in usernames) or (str(v['profile'].get('display_name')).lower() in usernames) ]
    for name in usernames:
        id=None
        for user in userlist:
            if (str(user.get('name')).lower() == name.lower()) or (str(user.get('real_name')).lower() == name.lower()) or (str(user['profile'].get('display_name')).lower() == name.lower()):
                id=user.get('id')
        userids[name]=id
    return userids

def getdmchannelid(userid,apitoken):
    #opens a slack channel for a direct message to a specified userid
    slack_client = SlackClient(apitoken)
    api_call = slack_client.api_call("im.open",user=userid)
    channel_id=api_call['channel']['id']
    return channel_id

def getallchannelids(channelids,userids,apitoken):
    #creates one list of channelids for channels and direct messages
    allchannelids=[]
    for user,userid in userids.items():
        if userid is not None:
            allchannelids.append(getdmchannelid(userid,apitoken))
    for channel,channelid in channelids.items():
        if channelid is not None:
            allchannelids.append(channelid)
    return allchannelids

'''__________NOTIFICATION FUNCTIONS___________'''

def processdelegates(delegatesnew,delegates):
    #compares the current and previous delegate block counts to track consecutive missed/produced blocks  
    delegatesold=delegates
    delegatesnew['missedblocksmsg']=0
    if delegates is None:
        #if no previous delegate block counts are available, start missed/produced block counters at 0 
        delegatesnew['newmissedblocks']=0
        delegatesnew['newproducedblocks']=0
        return delegatesnew
    else:
        delegates.rename(columns={'missedblocks': 'missedold','producedblocks':'producedold','missedblocksmsg':'msgold'}, inplace=True)
        delegates=delegates[['username','missedold','producedold','newmissedblocks','newproducedblocks','msgold']]
        delegatesnew=pd.merge(delegatesnew,delegates,how='left',on='username')
        delegatesnew['missedblocksmsg']=delegatesnew['missedblocksmsg']+delegatesnew['msgold']
        delegatesnew['newmissedblocks']=delegatesnew['newmissedblocks']+delegatesnew['missedblocks']-delegatesnew['missedold']
        #resets consecutive produced block counter to 0 if a delegate misses a block 
        delegatesnew.loc[delegatesnew['missedblocks']-delegatesnew['missedold']>0, ['newproducedblocks']] = 0
        delegatesnew['newproducedblocks']=delegatesnew['newproducedblocks']+delegatesnew['producedblocks']-delegatesnew['producedold']
        #resets consecutive missed block counter to 0 if a delegate produces a block 
        delegatesnew.loc[delegatesnew['producedblocks']-delegatesnew['producedold']>0, ['newmissedblocks','missedblocksmsg']] = 0
        #resets all counters to 0 if a delegate begins forging
        delegatesnew.loc[delegatesnew['newmissedblocks'].isnull(), ['newmissedblocks','missedblocksmsg','newproducedblocks']] = 0
        delegatesnew=delegatesnew.drop(['missedold','producedold','msgold'],axis=1)
        if len(delegatesnew[delegatesnew['newproducedblocks']<0].index)>0
	    delegatesnew=delegatesold
	return delegatesnew

def checknames(name):
    #creates a list of delegate name variations to compare with slack names
    names=[]
    names.append(name.lower())
    modifications={'_voting':'','_pool':''}
    for x,y in modifications.items():
        if x in name.lower():
            names.append(name.replace(x,y))
    return names

def makemissedblockmsglist(delegates,blockinterval,minmissedblocks,includeprevious=False):
    #creates a list of delegates that have missed blocks
    #when includeprevious is False, it will only include delegates that have either not previously been notified or have exceeded the blockinterval
    missedblockmsglist=[]
    for index, row in delegates.loc[delegates['newmissedblocks']>=minmissedblocks].iterrows():
        if includeprevious is False:
            if (row['newmissedblocks']>row['missedblocksmsg'])and((row['missedblocksmsg']<=1)or(row['newmissedblocks']-row['missedblocksmsg']>blockinterval)):
                missedblockmsglist.append({"username":row['username'],"missedblocksmsg":row['newmissedblocks']})
        else:
            missedblockmsglist.append({"username":row['username'],"missedblocksmsg":row['newmissedblocks']})
    for i in missedblockmsglist:
        delegates.loc[delegates['username']==i["username"], ['missedblocksmsg']] = i["missedblocksmsg"]
    return delegates,missedblockmsglist

def modifymissedblockmsglist(missedblockmsglist,slacknames,userlist):
    #modifies the list of users to notify to ping their slack username and id
    newmissedblockmsglist=[]
    for i in missedblockmsglist:
        delegate=i["username"]
        name=''
        names=checknames(delegate)
        for j in slacknames:
            if delegate == j["delegate"]:
                names.append(str(j["slackname"]).lower())
        for x in [v for v in userlist if (str(v.get('name')).lower() in names) or (str(v.get('real_name')).lower() in names) or (str(v['profile'].get('display_name')).lower() in names) ]:
            name="<@"+x.get('id')+">"
        i["username"]=delegate + ' ' + name + ' '
        newmissedblockmsglist.append(i)
    return newmissedblockmsglist

def makemissedblockmsg(missedblockmsglist,blockinterval=0,includeprevious=False):
    #creates a message to notify delegates of missed blocks
    #when includeprevious is False, it will only include delegates that have either not previously been notified or have exceeded the blockinterval
    if includeprevious is False:
        message=""
        for i in missedblockmsglist:
            if message!="":
                message=message+"\n"
            if i["missedblocksmsg"]>blockinterval:
                message=message+i["username"] +"still red :alert:"     
            elif i["missedblocksmsg"]>1:
                message=message+i["username"] +"red :alert:"
            else:
                message=message+i["username"] +"yellow :warning:"
    else:
        message=":alert: "
        for i in missedblockmsglist:
            if message != ":alert: ":
                message=message+", "+i["username"]
            else:
                message=message+i["username"]
        message=message+" :alert:"
    return message

'''__________RESPONSE FUNCTIONS___________'''

def getpools(file):
    pfile = open(file, 'r')
    pools = pfile.read()
    pfile.close
    pools = pools.replace('`','').lower()
    pools = max(pools.split('*'), key=len).split(';')
    pools = pd.DataFrame(pools,columns=['string'])
    pools['string'].str.lower()
    pools = pools['string'].str.extractall(r'^[*]?\s*\-*\s*(?P<delegate>[\w.-]+)?\,*\s*(?P<delegate2>[\w]+)?\,*\s*(?P<delegate3>[\w]+)?\,*\s*(?P<delegate4>[\w]+)?\,*\s*(?P<delegate5>[\w]+)?\,*\s<*(?P<website>[\w./:-]+)?>*\s*\(\`*[0-9x]*?(?P<percentage>[0-9.]+)\%\s*\-*(?P<listed_frequency>\w+)*\`*\,*\s*(?:min)?\.*\s*(?:payout)?\s*(?P<min_payout>[0-9.]+)*\s*(?P<coin>\w+)*?\s*(?:payout)?\`*[\w ]*\).*?$')
    dropcols=['coin']
    pools=pools.drop(dropcols,axis=1)
    pools.loc[pools['listed_frequency']=='c', ['listed_frequency']] = np.nan
    pools.loc[pools['listed_frequency']=='2d', ['listed_frequency']] = 2
    pools.loc[pools['listed_frequency']=='w', ['listed_frequency']] = 7
    pools.loc[pools['listed_frequency']=='d', ['listed_frequency']] = 1
    pools['listed_frequency']=pd.to_numeric(pools['listed_frequency'])
    pools['min_payout']=pd.to_numeric(pools['min_payout'])
    pools.rename(columns={'percentage': 'listed % share'}, inplace=True)
    pools=pd.melt(pools, id_vars=['listed % share','listed_frequency','min_payout','website'], var_name='delegatenumber', value_name='delegate')
    del pools['delegatenumber']
    pools=pools.loc[pools['delegate'].notnull()]
    pools=pools.reset_index(drop=True)
    pools['listed % share']=pd.to_numeric(pools['listed % share'])
    pools=pools.sort_values(by='listed % share',ascending=False)
    return pools

def getpoolstats(pools,delegates,numdelegates,blockrewards,blockspermin,balance=10000):
    delegates=delegates[['username','rank','vote','address']]
    totalrewardsperday=blockrewards*blockspermin*60*24/numdelegates
    poolstats=pd.merge(pools,delegates,how='left',left_on='delegate',right_on='username')
    poolstats['rewards/day']=((balance/poolstats['vote'])*totalrewardsperday*(poolstats['listed % share']/100)).round(2)
    del poolstats['username']
    poolstats=poolstats[poolstats['vote']>=0]
    poolstats['rank']=poolstats['rank'].astype('int64')
    poolstats['listed % share']=poolstats['listed % share'].astype('int64')
    del poolstats['vote']
    cols = list(poolstats)
    cols.insert(0, cols.pop(cols.index('rank')))
    poolstats = poolstats.ix[:, cols]
    poolstats=poolstats.sort_values(by='rewards/day',ascending=False)
    return poolstats

def printforgingpools(pools):
    cleanpools='*`Sharing Pools (Forging)`* -'
    pools['delegate']='_#'+pools['rank'].astype(str)+'_-*'+pools['delegate']+'*'
    pools=pools.groupby(['listed % share'])['delegate'].apply(', '.join).reset_index()
    pools=pools.sort_values(by='listed % share',ascending=False)
    for index,row in pools.iterrows():
        cleanpools+=' `'+str(row['listed % share'])+'%'+'` '+row['delegate']
    cleanpools+=' *_`We in no way endorse any of the pools shown here and only provide the list as a help to the community. The list only reflects the information we have been provided, we cannot police the pools and voters should do their due diligence before voting`_*'
    return cleanpools

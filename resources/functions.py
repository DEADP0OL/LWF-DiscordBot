import pandas as pd
import numpy as np
import requests
import json
import re
import time
import discord
from discord.ext import commands
from collections import defaultdict

'''___________SETUP FUNCTIONS___________'''

def getconfigs(file):
    #extracts configs from JSON file
    configs = json.load(open(file))
    apitoken = configs.get("discordapitoken")
    url = configs.get("apinode")
    backup = configs.get("backupnodes")
    port=configs.get("port")
    blockinterval = configs.get("blockintervalnotification")
    minmissedblocks = configs.get("minmissedblocks")
    servername = configs.get("server")
    channelnames = configs.get("channels")
    usernames = configs.get("users")
    numdelegates = configs.get("numdelegates")
    blockrewards = configs.get("blockrewards")
    blockspermin = configs.get("blockspermin")
    return apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin

def cleanurl(url,port):
    #removes url components to display node 
    cleanitems=['https://','http://','/',':'+port]
    for i in cleanitems:
        url=url.replace(i,'')
    return url

def getusernames(file):
    #gets username mappings from the JSON file
    usernames=json.load(open(file))
    return usernames

'''___________NODE API FUNCTIONS___________'''

def getdelegates(url,multiplier=100000000):
    #gets current delegates from the url node api
    delegates = pd.DataFrame(requests.get(url+'api/delegates?orderBy=vote').json()['delegates'])
    delegates['vote']=pd.to_numeric(delegates['vote'])/multiplier
    return delegates

def getpeers(url):
    #gets current peers from the url node api
    peers = pd.DataFrame(requests.get(url+'api/peers').json()['peers'])
    return peers

def getstatus(url,backup,port,tol=1):
    #gets current height from the list of backup nodes
    backupheights={}
    for i in backup:
        try:
            backupheights[cleanurl(i,port)]='{:,.0f}'.format(getheight(i))
        except:
            backupheights[cleanurl(i,port)]='not available'
    peers=getpeers(url)
    total=len(peers)
    peers=peers[peers['state']==2]    #filters to connected peers
    connectedpeers=len(peers)
    peerheight=peers['height'].mode()[0]    #calculates the mode height from connected peers
    consensus=round(len(peers[abs(peers['height']-peerheight)<=tol])/total*100,2) #calculates consensus from peer height
    backupheights['Peers: '+str(connectedpeers)]='{:,.0f}'.format(peerheight)
    backupheights['Consensus']='{:.0f}'.format(consensus)+'%'
    backupheights=pd.DataFrame.from_dict(backupheights,orient='index')
    backupheights.columns = ['Height']
    return connectedpeers,peerheight,consensus,backupheights

def getheight(url):
    #gets current block height from the url node api
    height = requests.get(url+'api/blocks/getHeight').json()['height']
    return height

'''___________Discord API FUNCTIONS___________'''

def getchannel(channelname,server):
    #returns the channel object
    channel = discord.utils.find(lambda m: (m.name).lower() == channelname.lower(), server.channels)
    return channel

def getuser(username,server):
    #returns the member object
    user = discord.utils.find(lambda m: (m.name).lower() == username.lower(), server.members)
    return user

def getuserids(usernames,server):
    #gets userids for specified usernames in a discord team userlist
    userids={}
    usernames=[v.lower() for v in usernames]
    userlist=server.members
    userlist=[v for v in userlist if str(v.name).lower() in usernames]
    for name in usernames:
        id=None
        for user in userlist:
            if str(user.name).lower() == name.lower():
                id=user
        userids[name]=id
    return userids

def formatmsg(message,maxlen=1990,prefix1='```',style='',prefix2='\n',suffix='\n```',seps=[' ',',']):
    #breaks the message up according to discords text limit and adds code blocks by default
    messages=[]
    messagelen=len(message)
    b=0
    while b<messagelen:
        a=b
        if a+maxlen>=messagelen:
            b=messagelen
        else:
            for i in seps:
                b2=message[a:min(a+maxlen,messagelen)].rfind(i)+a
                if b2>b:
                    b=b2
                else:
                    b2=-1
            if b<=a:
                b=min(messagelen,a+maxlen)
        messages.append(prefix1+style+prefix2+message[a:b]+suffix)
    return messages

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
        if len(delegatesnew[delegatesnew['newproducedblocks']<0].index)>0:
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

def modifymissedblockmsglist(missedblockmsglist,discordnames,server):
    #modifies the list of users to notify to ping their slack username and id
    userlist=server.members
    newmissedblockmsglist=[]
    for i in missedblockmsglist:
        delegate=i["username"]
        name=''
        display=''
        names=checknames(delegate)
        for j in discordnames:
            if delegate == j["delegate"]:
                names.append(str(j["discordname"]).lower())
        for x in [v for v in userlist if str(v.name).lower() in names]:
            name='<@{}>'.format(str(x.id))
            display=x.name
        if str(display).lower()==delegate.lower():
            i["username"]=name + ' '
        else:
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
                message=message+i["username"] +"still red :red_circle:"
            elif i["missedblocksmsg"]>1:
                message=message+i["username"] +"red :red_circle:"
            else:
                message=message+i["username"] +"yellow :warning:"
    else:
        redmessage=":red_circle: "
        yellowmessage=":warning: "
        for i in missedblockmsglist:
            if i["missedblocksmsg"]>1:
                if redmessage != ":red_circle: ":
                    redmessage+=", "+i["username"]
                else:
                    redmessage+=i["username"]
            else:
                if yellowmessage != ":warning: ":
                    yellowmessage+=", "+i["username"]
                else:
                    yellowmessage+=i["username"]
        redmessage+=":red_circle:"
        yellowmessage+=":warning:"
        if redmessage != ":red_circle: :red_circle:":
            message=redmessage
            if yellowmessage != ":warning: :warning:":
                message+="\n"+yellowmessage
        elif yellowmessage != ":warning: :warning:":
            message=yellowmessage
    return message

'''__________RESPONSE FUNCTIONS___________'''

def getpools(file):
    #parses pools from raw string stored in a local file
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
    #merges pool data with current delegate api results
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
    #filters the pools based on rank and groups them by sharing percentage
    bld='**'
    ul='__'
    cleanpools='*`Sharing Pools (Forging)`* -'
    pools=pools.sort_values(by='rank')
    #pools['delegate']='_#'+pools['rank'].astype(str)+'_-**'+pools['delegate']+'**'
    pools['delegate']=ul+pools['delegate']+ul
    pools=pools.groupby(['listed % share'])['delegate'].apply(', '.join).reset_index()
    pools=pools.sort_values(by='listed % share',ascending=False)
    for index,row in pools.iterrows():
        cleanpools+=' '+bld+str(row['listed % share'])+'%'+bld+' '+row['delegate']
    cleanpools+=' We in no way endorse any of the pools shown here and only provide the list as a help to the community. The list only reflects the information we have been provided, we cannot police the pools and voters should do their due diligence before voting.'
    return cleanpools

def printdelegates(delegates):
    #outputs the delegates list in a friendly format
    bld='**'
    ul='__'
    #delegates['voteweight'] = round(delegates['vote']/1000,).astype(str) + 'K'
    delegates['voteweight'] = (delegates['vote']/1000).map('{:,.0f}'.format).astype(str) + 'K'
    cleandelegates=delegates[['rank','username','approval','voteweight']].to_string(index=False)
    return cleandelegates

def getprice(priceurl,coin,suffix='/'):
    #retrieves the price data for a specified coin
    url=priceurl+coin.lower()+suffix
    request=requests.get(url).json()
    data=request[0]
    price_usd=data['price_usd']
    #price_btc=data['price_btc']
    leaveout=['id','last_updated']
    for key in leaveout:
        data.pop(key, None)
    pricesummary=pd.DataFrame.from_dict(data,orient='index')
    pricesummary=pricesummary.to_string(header=False)
    return price_usd,pricesummary

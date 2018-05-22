import pandas as pd
import numpy as np
import requests
import json
import re
import time
import discord
import asyncio
from discord.ext import commands
from collections import defaultdict

'''___________SETUP FUNCTIONS___________'''

def getconfigs(file):
    """extracts configs from JSON file"""
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
    testurl = configs.get("testapinode")
    testbackup = configs.get("testbackupnodes")
    testport=configs.get("testport")
    notificationmins=configs.get("notificationmins")
    commandprefix=configs.get("commandprefix")
    return apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin,testurl,testbackup,testport,notificationmins,commandprefix

def cleanurl(url,port):
    """removes url components to display node""" 
    cleanitems=['https://','http://','/',':'+port]
    for i in cleanitems:
        url=url.replace(i,'')
    return url

def getusernames(file):
    """gets username mappings from the JSON file"""
    usernames=json.load(open(file))
    return usernames

'''___________NODE API FUNCTIONS___________'''

def getdelegates(url,multiplier=100000000,numdelegates=201):
    """gets current delegates from the url node api"""
    i=0
    minrank=numdelegates+50
    delegates = pd.DataFrame(requests.get(url+'api/delegates?orderBy=vote').json()['delegates'])
    delegates['vote']=pd.to_numeric(delegates['vote'])/multiplier
    delegates['approval']=pd.to_numeric(delegates['approval'])
    lowestrank = delegates['rank'].iloc[-1]
    length = len(delegates)
    while lowestrank<=minrank:
        i=i+length
        delegates1 = pd.DataFrame(requests.get(url+'api/delegates?offset='+str(i)+'&orderBy=vote').json()['delegates'])
        if not delegates1.empty:
            delegates1['vote']=pd.to_numeric(delegates1['vote'])/multiplier
            delegates1['approval']=pd.to_numeric(delegates1['approval'])
            lowestrank = delegates['rank'].iloc[-1]
            delegates=delegates.append(delegates1,ignore_index=True)
        else:
            lowestrank = minrank+1
    delegates=delegates.loc[delegates['rank']<=minrank]
    return delegates

def getpeers(url):
    """gets current peers from the url node api"""
    peers = pd.DataFrame(requests.get(url+'api/peers').json()['peers'])
    return peers

def getstatus(url,backup,port,tol=1):
    """gets current height from the list of backup nodes"""
    backupheights={}
    for i in backup:
        try:
            backupheights[cleanurl(i,port)]='{:,.0f}'.format(getheight(i))
        except:
            backupheights[cleanurl(i,port)]='not available'
    try:
        peers=getpeers(url)
        total=len(peers)
        peers=peers[peers['state']==2]    #filters to connected peers
        connectedpeers=len(peers)
        peerheight=peers['height'].mode()[0]    #calculates the mode height from connected peers
        consensus=round(len(peers[abs(peers['height']-peerheight)<=tol])/total*100,2) #calculates consensus from peer height
        backupheights['Peers: '+str(connectedpeers)]='{:,.0f}'.format(peerheight)
        backupheights['Consensus']='{:.1f}%'.format(consensus)
    except:
        connectedpeers='not available'
        peerheight='not available'
        consensus='not available'
        backupheights['Peers: '+connectedpeers]=peerheight
        backupheights['Consensus']=consensus
    backupheights=pd.DataFrame.from_dict(backupheights,orient='index')
    backupheights.columns = ['Height']
    return connectedpeers,peerheight,consensus,backupheights

def getheight(url):
    """gets current block height from the url node api"""
    height = requests.get(url+'api/blocks/getHeight').json()['height']
    return height

'''___________DISCORD API FUNCTIONS___________'''

def getchannel(channelname,server):
    """returns the channel object"""
    channel = discord.utils.find(lambda m: (m.name).lower() == channelname.lower(), server.channels)
    return channel

def getuser(username,server):
    """returns the member object"""
    user = discord.utils.find(lambda m: (m.name).lower() == username.lower(), server.members)
    return user

def getuserids(usernames,server):
    """gets userids for specified usernames in a discord team userlist"""
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
    """breaks the message up according to discords text limit and adds code blocks by default"""
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

def discordembeddict(dictionary,exclude=[],title='',url='',color=0x0080c0,footer='',inline=True):
    """extracts data from dictionary as a discord embed object"""
    embed=discord.Embed(title=title,url=url, color=color)
    for key,result in dictionary.items():
        if (key not in exclude):
            embed.add_field(name=key, value=result, inline=inline)
    embed.set_footer(text=footer)
    return embed

'''__________NOTIFICATION FUNCTIONS___________'''

def processdelegates(delegatesnew,delegates):
    """compares the current and previous delegate block counts to track consecutive missed/produced blocks"""
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
    """creates a list of delegate name variations to compare with slack names"""
    names=[]
    names.append(name.lower())
    modifications={'_voting':'','_pool':''}
    for x,y in modifications.items():
        if x in name.lower():
            names.append(name.replace(x,y))
    return names

def makemissedblockmsglist(delegates,blockinterval,minmissedblocks,includeprevious=False,numdelegates=201):
    """creates a list of delegates that have missed blocks. When includeprevious is False, 
    it will only include delegates that have either not previously been notified or have exceeded the blockinterval"""
    missedblockmsglist=[]
    for index, row in delegates.loc[(delegates['newmissedblocks']>=minmissedblocks)&(delegates['rank']<=numdelegates)].iterrows():
        if includeprevious is False:
            if (row['newmissedblocks']>row['missedblocksmsg'])and((row['missedblocksmsg']<=1)or(row['newmissedblocks']-row['missedblocksmsg']>blockinterval)):
                missedblockmsglist.append({"username":row['username'],"missedblocksmsg":row['newmissedblocks']})
        else:
            missedblockmsglist.append({"username":row['username'],"missedblocksmsg":row['newmissedblocks']})
    for i in missedblockmsglist:
        delegates.loc[delegates['username']==i["username"], ['missedblocksmsg']] = i["missedblocksmsg"]
    return delegates,missedblockmsglist

def modifymissedblockmsglist(missedblockmsglist,discordnames,server):
    """modifies the list of users to notify to ping their discord username"""
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
    """creates a message to notify delegates of missed blocks. When includeprevious is False,
    it will only include delegates that have either not previously been notified or have exceeded the blockinterval"""
    if includeprevious is False:
        message=""
        for i in missedblockmsglist:
            if message!="":
                message=message+"\n"
            if i["missedblocksmsg"]>blockinterval:
                message=message+i["username"] +"still red :no_entry:"
            elif i["missedblocksmsg"]>1:
                message=message+i["username"] +"red :no_entry:"
            else:
                message=message+i["username"] +"yellow :warning:"
    else:
        redmessage=":no_entry: "
        yellowmessage=":warning: "
        for i in missedblockmsglist:
            if i["missedblocksmsg"]>1:
                if redmessage != ":no_entry: ":
                    redmessage+=", "+i["username"]
                else:
                    redmessage+=i["username"]
            else:
                if yellowmessage != ":warning: ":
                    yellowmessage+=", "+i["username"]
                else:
                    yellowmessage+=i["username"]
        redmessage+=":no_entry:"
        yellowmessage+=":warning:"
        if redmessage != ":no_entry: :no_entry:":
            message=redmessage
            if yellowmessage != ":warning: :warning:":
                message+="\n"+yellowmessage
        elif yellowmessage != ":warning: :warning:":
            message=yellowmessage
    return message

'''__________RESPONSE FUNCTIONS___________'''

def getpools(file):
    """parses pools from raw string stored in a local file"""
    pools,poolerrors=poolsstringtodf(file)
    pools=pd.melt(pools, id_vars=['listed % share','listed_frequency','min_payout','website'], var_name='delegatenumber', value_name='delegate')
    del pools['delegatenumber']
    pools=pools.loc[pools['delegate'].notnull()]
    pools=pools.reset_index(drop=True)
    pools['listed % share']=pd.to_numeric(pools['listed % share'])
    pools=pools.sort_values(by='listed % share',ascending=False)
    return pools,poolerrors

def getpoolstats(pools,delegates,numdelegates,blockrewards,blockspermin,balance=10000):
    """merges pool data with current delegate api results"""
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

def printforgingpools(pools,numdelegates=201):
    """filters the pools based on rank and groups them by sharing percentage"""
    #bld='**'
    #ul='__'
    bld=''
    ul=''
    cb='`'
    it=''
    #it='_'
    file='http://verifier.dutchpool.io/lwf/report.json'
    pools=pools.loc[pools['rank']<=numdelegates]
    pools=pools.sort_values(by='rank')
    try:
        actualshare=requests.get(file).json()['delegates']
        actualshare=pd.DataFrame.from_dict(actualshare)
        pools=pd.merge(pools,actualshare,how='left',left_on='delegate',right_on='name')
        pools.loc[(pools['percentage']>=0) & (pools['method']!='simple'),'delegate']=ul+pools['delegate']+ul+'-'+cb+pools['percentage'].apply(lambda x: "{:.0f}".format(x))+'%'+cb
        pools.loc[(pools['percentage']>=0) & (pools['method']=='simple'),'delegate']=ul+pools['delegate']+ul+'-'+it+cb+pools['percentage'].apply(lambda x: "{:.0f}".format(x))+'%**'+cb+it
        pools.loc[pools['percentage']==np.nan,'delegate']=ul+pools['delegate']+ul
        footer='The percentage shown to the right of each delegate is an estimated sharing percentage provided by http://verifier.dutchpool.io/lwf.'
        footer+='\n'+cb+'**'+cb+' No regular reward sharing transactions detected. Take this calculated share with a grain of salt.'
    except:
        pools['delegate']=ul+pools['delegate']+ul
        footer=''
    pools=pools.groupby(['listed % share'])['delegate'].apply(', '.join).reset_index()
    pools=pools.sort_values(by='listed % share',ascending=False)
    cleanpools='\t'+ul+bld+it+'Sharing Pools'+it+bld+ul+'\n'
    for index,row in pools.iterrows():
        cleanpools+=bld+cb+str(row['listed % share'])+'% Pools:'+cb+bld+' '+row['delegate']+'\n'
    cleanpools+=footer
    return cleanpools

def printdelegates(delegates,rank,limit):
    """outputs the delegates list in a friendly format"""
    delegates=delegates.loc[(delegates['rank']>=rank-limit)&(delegates['rank']<=rank+limit)]
    delegates['voteweight'] = (delegates['vote']/1000).map('{:,.0f}'.format).astype(str) + 'K'
    delegates['productivity'] = delegates['productivity'].map('{:,.1f}%'.format)
    delegates['approval'] = delegates['approval'].map('{:,.2f}%'.format)
    ind=(delegates['rank'].values.tolist()).index(rank)
    delegates=insertblankrow(delegates,ind+1)
    cleandelegates=delegates[['rank','username','approval','voteweight','productivity']].to_string(index=False)
    return cleandelegates

def getprice(priceurl,coin,conv='',suffix='/'):
    """retrieves the price data for a specified coin"""
    coin=coin.replace(' ','-')
    if conv =='':
        url=priceurl+coin.lower()+suffix
        leaveout=['id','last_updated','max_supply','available_supply','total_supply']
    else:
        url=priceurl+coin.lower()+suffix+'?convert='+conv
        leaveout=['id','last_updated','max_supply','available_supply','total_supply','price USD','24h_volume USD','Change 1h','Change 24h','Change 7d']
    request=requests.get(url).json()
    data=request[0]
    data2=data.copy()
    for key,value in data2.items():
        if '_usd' in key:
            try:
                if float(value)>1000000:
                    data[key.replace('_usd',' USD')]="${:,.2f}MM".format(float(value)/1000000)
                elif float(value)>10000:
                    data[key.replace('_usd',' USD')]="${:,.2f}K".format(float(value)/1000)
                elif float(value)>1000:
                    data[key.replace('_usd',' USD')]="${:,.0f}".format(float(value))
                elif float(value)>1:
                    data[key.replace('_usd',' USD')]="${:,.2f}".format(float(value))
                elif float(value)>.1:
                    data[key.replace('_usd',' USD')]="${:,.3f}".format(float(value))
                elif float(value)>.01:
                    data[key.replace('_usd',' USD')]="${:,.4f}".format(float(value))
                else:
                    data[key.replace('_usd',' USD')]='$'+str(value)
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif '_btc' in key:
            try:
                if float(value)>10000:
                    data[key.replace('_btc',' BTC')]="{:,.2f}K BTC".format(float(value)/1000)
                elif float(value)>1000:
                    data[key.replace('_btc',' BTC')]="{:,.0f} BTC".format(float(value))
                else:
                    data[key.replace('_btc',' BTC')]="{:,.3f} BTC".format(float(value))
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif (conv.upper()!='BTC')and(conv!='')and('_'+conv.lower() in key):
            try:
                if float(value)>10000:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.2f}K".format(float(value)/1000)+' '+conv.upper()
                elif float(value)>1000:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.0f}".format(float(value))+' '+conv.upper()
                else:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.3f}".format(float(value))+' '+conv.upper()
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif 'percent_change_' in key:
            try:
                if float(value)>0:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))+' :arrow_up_small:'
                elif float(value)<0:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))+' :arrow_down_small:'
                else:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
    if conv=='':
        price=data['price USD']
    elif conv.upper()!='BTC':
        field='price '+conv.upper()
        price=data[field]
        leaveout.append('price BTC')
    else:
        price=data['price BTC']
    for key in leaveout:
        data.pop(key, None)
    pricesummary=data
    return price,pricesummary

def insertblankrow(df,ind):
    """inserts a blank row into a dataframe at the specified index"""
    cols=list(df.columns.values)
    blank=pd.Series([''],index=cols)
    result=df.iloc[:ind].append(blank,ind)
    result=result.append(df.iloc[ind:],ind)
    return result

def poolsdftojson(poolsdf,file='files/pools.json'):
    """Converts a dataframe to JSON format for storage"""
    poolsdf['listed % share']=pd.to_numeric(poolsdf['listed % share'])
    poolsdf=poolsdf.sort_values(by='listed % share',ascending=False)
    poolsjson=poolsdf.to_json(orient='records')
    with open(file, 'w') as f:
        f.write(poolsjson)
    return poolsjson

def poolsjsontostring(poolsjson,file='files/pools.txt'):
    """Converts a string in JSON format to a string for communication"""
    prefix = '*_`Sharing Pools`_* - '
    suffix = '*`KEY`* _Month = (M), Week = (W), Daily = (D), 2 Day = (2D), Custom = (C) - speak with delegate._  *_`We in no way endorse any of the pools shown here and only provide the list as a help to the community. The list only reflects the information we have been provided, we cannot police the pools and voters should do their due diligence before voting`_*'
    poolsstring=prefix
    poolsjson=json.loads(poolsjson)
    for i in poolsjson:
        number = 0
        pool=''
        for key,value in i.items():
            if (value is not None) and 'delegate' in key:
                if pool=='':
                    pool+=value
                else:
                    pool+=', '+value
                number+=1
        value=i.get('website')
        if value is not None:
            pool+=' '+value
        pool+=' (`'
        value=i.get('listed % share')
        if value is not None:
            if number > 1:
                pool+=str(number)+'x'+str(value)+'%'
            else:
                pool+=str(value)+'%'
        value=i.get('listed_frequency')
        if value is not None:
            if value==1:
                pool+='-d'
            elif value==7:
                pool+='-w'
            else:
                pool+='-'+str(value)+'d'
        pool+='`'
        value=i.get('min_payout')
        if value is not None:
            if value == 1.0:
                pool+=', min payout '+str(int(value))
            elif value == 2.0:
                pool+=', min payout '+str(int(value))
            else:
                pool+=', min payout '+str(value)
        pool+='); '
        poolsstring+=pool
    poolsstring+=suffix
    with open(file, 'w') as f:
        f.write(poolsstring)
    return poolsstring

def poolsstringtodf(file,loaded=False):
    """opens a text file and interprets the data as a dataframe"""
    rgex=r'^[*]?\s*\-*\s*(?P<delegate>[\w.-]+)\,*\s*(?P<delegate2>[\w]+)?\,*\s*(?P<delegate3>[\w]+)?\,*\s*(?P<delegate4>[\w]+)?\,*\s*(?P<delegate5>[\w]+)?\,*\s<*(?P<website>[\w./:-]+)?>*\s*\(\`*[0-9x]*?(?P<percentage>[0-9.]+)\%\s*\-*(?P<listed_frequency>\w+)*\`*\,*\s*(?:min)?\.*\s*(?:payout)?\s*(?P<min_payout>[0-9.]+)*\s*(?P<coin>\w+)*?\s*(?:payout)?\`*[\w -/]*\).*?$'
    if loaded is False:
        pfile = open(file, 'r')
        pools = pfile.read()
        pfile.close
    else:
        pools=file
    pools = pools.replace('`','').lower()
    pools = max(pools.split('*'), key=len).split(';')
    pools = pd.DataFrame(pools,columns=['string'])
    pools['string'] = pools['string'].str.lower()
    poolerrors=pools
    poolerrors['match']=poolerrors['string'].str.findall(rgex)
    poolerrors=poolerrors.loc[(poolerrors['string']!='')&(poolerrors['string']!=' ')]
    poolerrors=poolerrors.loc[poolerrors.match.str.len()==0,'string']
    pools = pools['string'].str.extractall(rgex)
    pools.loc[pools['listed_frequency']=='c', ['listed_frequency']] = ''
    pools.loc[pools['listed_frequency']=='2d', ['listed_frequency']] = '2'
    pools.loc[pools['listed_frequency']=='w', ['listed_frequency']] = '7'
    pools.loc[pools['listed_frequency']=='d', ['listed_frequency']] = '1'
    pools['listed_frequency']=pd.to_numeric(pools['listed_frequency'])
    pools['min_payout']=pd.to_numeric(pools['min_payout'])
    pools.rename(columns={'percentage': 'listed % share'}, inplace=True)
    dropcols=['coin']
    pools=pools.drop(dropcols,axis=1)
    return pools,poolerrors

def addpool(string,file):
    poolsdf,poolerrors=poolsstringtodf(file)
    pools2df,pool2errors=poolsstringtodf(string,True)
    poolsdf=poolsdf.append(pools2df,ignore_index=True)
    poolsjson=poolsdftojson(poolsdf)
    poolsstring=poolsjsontostring(poolsjson)
    return poolsstring

def removepool(string,file):
    poolsdf,poolerrors=poolsstringtodf(file)
    cols=list(poolsdf.columns.values)
    cols=cols[0:5]
    for i in cols:
        poolsdf=poolsdf.loc[poolsdf[i]!=string.lower()]
    poolsjson=poolsdftojson(poolsdf)
    poolsstring=poolsjsontostring(poolsjson)
    return poolsstring

def resetpools(url,file):
    url = 'https://raw.githubusercontent.com/DEADP0OL/LWF-DiscordBot/master/files/pools.txt'
    poolsstring=requests.get(url).text
    with open(file, 'w') as f:
        f.write(poolsstring)
    return poolsstring

def poolcheck(string):
    rgex=r'^[*]?\s*\-*\s*(?P<delegate>[\w.-]+)\,*\s*(?P<delegate2>[\w]+)?\,*\s*(?P<delegate3>[\w]+)?\,*\s*(?P<delegate4>[\w]+)?\,*\s*(?P<delegate5>[\w]+)?\,*\s<*(?P<website>[\w./:-]+)?>*\s*\(\`*[0-9x]*?(?P<percentage>[0-9.]+)\%\s*\-*(?P<listed_frequency>\w+)*\`*\,*\s*(?:min)?\.*\s*(?:payout)?\s*(?P<min_payout>[0-9.]+)*\s*(?P<coin>\w+)*?\s*(?:payout)?\`*[\w -/]*\).*?$'
    result=re.findall(rgex,string)
    if len(result)>0:
        return True
    else:
        return False
    
def unmatchedpools(pools,delegates):
    unmatchedlist=pools.loc[~pools['delegate'].isin(delegates['username']),'delegate']
    if len(unmatchedlist)==0:
        return {'check':False,'unmatched':None}
    else:
        return {'check':True,'unmatched':unmatchedlist}

def duplicatepools(pools):
    pools=pools['delegate']
    duplicatelist=pools.loc[pools.duplicated(keep=False)]
    if len(duplicatelist)==0:
        return {'check':False,'duplicates':None}
    else:
        return {'check':True,'duplicates':duplicatelist}

def getpoolerrors(pools,poolerrors,delegates):
    response=''
    if len(poolerrors)>0:
        response+='Pools not formatted correctly:\n'
        response+=poolerrors.to_string(index=False)
        response+='\n'
    unmatched=unmatchedpools(pools,delegates)
    if unmatched['check']:
        response+='Pools not found in delegate list:\n'
        response+=unmatched['unmatched'].to_string(index=False)
        response+='\n'
    duplicates=duplicatepools(pools)
    if duplicates['check']:
        response+='Pools that are duplicated:\n'
        response+=duplicates['duplicates'].to_string(index=False)
        response+='\n'
    if response=='':
        response='No errors'
    return response

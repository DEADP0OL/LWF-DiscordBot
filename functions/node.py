import pandas as pd
import requests
import datetime

'''___________NODE/API FUNCTIONS___________'''

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

def getstatus(url,backup,port,hosts={},tol=1):
    """gets current height from the list of backup nodes"""
    backupheights={}
    for i in backup:
        try:
            if i in hosts:
                backupheights[cleanurl(i,port)]='{:,.0f}'.format(getheight(hosts[i]))
            else:
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

def getchecksum(url):
    req = requests.get(url).json()
    req["last_modified"]=datetime.datetime.utcfromtimestamp(req.get("last_modified")).strftime('%Y-%m-%d %H:%M:%S GMT')
    req["height"]="{:,}".format(int(req["height"]))
    req = pd.DataFrame.from_dict(req, orient='index')
    return req.to_string(header=False)
        
def getheight(url):
    """gets current block height from the url node api"""
    height = requests.get(url+'api/blocks/getHeight',timeout=1).json()['height']
    return height

def cleanurl(url,port):
    """removes url components to display node"""
    cleanitems=['https://','http://','/',':'+port]
    for i in cleanitems:
        url=url.replace(i,'')
    return url
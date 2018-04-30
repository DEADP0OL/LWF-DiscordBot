from resources.functions import *
#obtain config variables
apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin,testurl,testbackup,testport=getconfigs('resources/config.json')
delegatesnew=getdelegates(testurl)
try:
    delegates = pd.read_csv("files/testnet-delegates.csv",index_col=0)
except FileNotFoundError:
    delegates=None
    print("Counters Initialized")
delegates=processdelegates(delegatesnew,delegates)
delegates.to_csv('files/testnet-delegates.csv')

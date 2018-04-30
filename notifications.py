from resources.functions import *
#obtain config variables
apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin,testurl,testbackup,testport=getconfigs('resources/config.json')
delegatesnew=getdelegates(url)
try:
    delegates = pd.read_csv("files/delegates.csv",index_col=0)
except FileNotFoundError:
    delegates=None
    print("Counters Initialized")
delegates=processdelegates(delegatesnew,delegates)
delegates,missedblockmsglist=makemissedblockmsglist(delegates,blockinterval,minmissedblocks)
delegates.to_csv('files/delegates.csv')
if len(missedblockmsglist)>0:
    client = discord.Client()
    @client.event
    async def on_ready():
        discordnames=getusernames('resources/discordnames.json')
        server = discord.utils.find(lambda m: (m.name).lower() == servername, client.servers)
        newmissedblockmsglist=modifymissedblockmsglist(missedblockmsglist,discordnames,server)
        message=makemissedblockmsg(newmissedblockmsglist,blockinterval)
        for channelname in channelnames:
            await client.send_message(getchannel(channelname,server), message)
        for username in usernames:
            await client.send_message(getuser(username,server), message)
        client.close()
    client.run(apitoken)

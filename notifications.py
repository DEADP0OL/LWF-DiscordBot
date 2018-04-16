from functions import *
#obtain config variables
apitoken,url,backup,port,blockinterval,minmissedblocks,channelnames,usernames,numdelegates,blockrewards,blockspermin=getconfigs('config.json')
message =''

delegatesnew=getdelegates(url)
if message =='':
    try:
        delegates = pd.read_csv("delegates.csv",index_col=0)
    except FileNotFoundError:
        delegates=None
        print("Counters Initialized")
    delegates=processdelegates(delegatesnew,delegates)
    delegates,missedblockmsglist=makemissedblockmsglist(delegates,blockinterval,minmissedblocks)
    delegates.to_csv('delegates.csv')
    if len(missedblockmsglist)>0:
        slacknames=getusernames('slacknames.json')
        userlist=getuserlist(apitoken)
        missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,slacknames,userlist)
        message=makemissedblockmsg(missedblockmsglist,blockinterval)
#sends the message to specified channels
if message !='':
    slack_client = SlackClient(apitoken)
    channelids=getchannelids(channelnames,apitoken)
    userids=getuserids(usernames,apitoken)
    allchannelids=getallchannelids(channelids,userids,apitoken)
    for channel_id in allchannelids:
        slack_client.api_call("chat.postMessage",channel=channel_id,text=message,as_user=True)

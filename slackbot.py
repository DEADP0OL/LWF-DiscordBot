#!/usr/bin/env python3

import time
from functions import *

#obtain config variables and initiate slack client
apitoken,url,backup,port,blockinterval,minmissedblocks,channelnames,usernames,numdelegates,blockrewards,blockspermin=getconfigs('config.json')
slack_client = SlackClient(apitoken)
slacknames=getusernames('slacknames.json')
userlist=getuserlist(apitoken)

# slackbot unique constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "help, red nodes, height, pools, forging pools"
HELP_COMMAND = EXAMPLE_COMMAND.replace('help, ','')
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
POOLLIST_REGEX = "^\*_`([\w ]+)`_\*(.*)"
POOLSTXTFILE="pools.txt"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function checks for a pool list.
        If that is also not foudn this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_calls(event["text"],MENTION_REGEX)
            if user_id == starterbot_id:
                return message.lower(), event["channel"]
            else:
                poollist, pools = parse_direct_calls(event["text"],POOLLIST_REGEX)
                if poollist=="Sharing Pools" and len(pools)>1000:
                    pooltext='*_`'+poollist+'`_*'+pools
                    f= open(POOLSTXTFILE,"w+")
                    f.write(pooltext)
                    f.close
    return None, None

def parse_direct_calls(message_text,REGEX):
    """
        Runs a regex search and returns the first two groups. The second group is stripped of white spaces.
        Returns None,None if regex search criteria are not met.
    """
    matches = re.search(REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Determines an appropriate response for the determined command and replies on the channel.
    """
    # help response
    if command.startswith('help'):
        response = "Available commands: *{}*.".format(HELP_COMMAND)
    # red nodes response
    elif command.startswith('red nodes'):
        delegates = pd.read_csv("delegates.csv",index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True)
        if len(missedblockmsglist)>0:
            missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,slacknames,userlist)
            response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = "No red nodes"
    # pools forging
    elif command.startswith('pools forging') or command.startswith('forging pools'):
        pools= getpools(POOLSTXTFILE)
        delegates = pd.read_csv("delegates.csv",index_col=0)
        poolstats=getpoolstats(pools,delegates,numdelegates,blockrewards,blockspermin)
        response=printforgingpools(poolstats)
    # pools response
    elif command.startswith('pools'):
        file= open(POOLSTXTFILE,"r")
        response=file.read()
        file.close
    # blockchain/connection status
    elif command.startswith('height') or command.startswith('block height') or command.startswith('status'):
        connectedpeers,peerheight,consensus,backupheights=getstatus(url,backup)
        response=''
        for key,value in backupheights.items():
            response+=cleanurl(key,port)+ ' Height: '+str(value)+'\n'
        response+='Peer Count: {}, Peer Height: {}\nConsensus: {}%'.format(connectedpeers,peerheight,consensus)
    # default response for unknown commands
    else:
        response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response,
        as_user=True
    )

if __name__ == "__main__":
    while True:
        if slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`
            starterbot_id = slack_client.api_call("auth.test")["user_id"]
            while True:
                command, channel = parse_bot_commands(slack_client.rtm_read())
                if command:
                    handle_command(command, channel)
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Retrying...")
            time.sleep(RTM_READ_DELAY*5)

#!/usr/bin/env python3

from resources.functions import *

'''obtain config variables and initiate slack client'''
apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin=getconfigs('resources/config.json')
command='?'
example_command = "help, price, delegate, delegates, rednodes, height, pools, forgingpools"
help_command = example_command.replace('help, ','')
description='A bot with scripts to analyze the LWF blockchain in addition to other relevant dynamic information. Use commands in conjunction with a direct bot mention or the command prefix "?".'
poolstxtfile="files/pools.txt"
delegatecsv="files/delegates.csv"
discordnames=getusernames('resources/discordnames.json')
msglimit=1800
priceurl='https://api.coinmarketcap.com/v1/ticker/'

bot = commands.Bot(command_prefix=commands.when_mentioned_or(command), description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    server = discord.utils.find(lambda m: (m.name).lower() == servername, list(bot.servers))
    print(server)
    print('------')

@bot.command(pass_context=True)
async def price(ctx,coin='lwf'):
    """Retrieves price data for a specified coin. Ex: ?price bitcoin"""
    assert ctx.message.channel.name in channelnames
    try:
        price,pricesummary=getprice(priceurl, coin)
        embed=discordembeddict(pricesummary,['name'],pricesummary['name'],"https://coinmarketcap.com/currencies/"+coin)
        await bot.say(embed=embed)
    except:
        await bot.say('Command incorrect, try '+command+'price bitcoin')
        return

@bot.command(pass_context=True)
async def delegate(ctx,delegate='',limit=10):
    """Filters the delegate list by name or rank. Ex: ?delegate deadpool"""
    assert ctx.message.channel.name in channelnames
    delegates = pd.read_csv(delegatecsv,index_col=0)
    try:
        if delegate=='':
            response='Enter a delegate name or rank. Try '+command+'delegate 1'
        elif not delegate.isdigit():
            if delegate.lower() in delegates['username'].str.lower().values:
                rank=delegates.loc[delegates['username'].str.lower() == delegate.lower(), 'rank'].iloc[0]
                response=printdelegates(delegates,rank,limit)
            else:
                response='Cannot find that delegate'
        else:
            rank=int(delegate)
            if rank in delegates['rank'].values:
                response=printdelegates(delegates,rank,limit)
            else:
                response='Cannot find that delegate rank'
    except:
        await bot.say('Not sure what you mean. Try '+command+'delegate 1')
        return
    for response in formatmsg(response,msglimit,'```','','\n','\n```',seps=['\n']):
        await bot.say(response)
    
@bot.command(pass_context=True)
async def delegates(ctx,limit=10):
    """Returns the delegate list in order of rank."""
    assert ctx.message.channel.name in channelnames
    rank=numdelegates
    delegates = pd.read_csv(delegatecsv,index_col=0)
    response=printdelegates(delegates,rank,limit)
    for response in formatmsg(response,msglimit,'```','','\n','\n```',seps=['\n']):
        await bot.say(response)

@bot.command(pass_context=True)
async def rednodes(ctx,net='mainnet'):
    """Lists delegates that are currently missing blocks."""
    assert ctx.message.channel.name in channelnames
    assert net=='mainnet' or net=='testnet'
    if net=='testnet':
        delegates = pd.read_csv(testdelegatecsv,index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True)
        if len(missedblockmsglist)>0:
            server = discord.utils.find(lambda m: (m.name).lower() == servername, list(bot.servers))
            userlist=server.members
            missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,testdiscordnames,server)
            response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = 'No red nodes'
    else:
        delegates = pd.read_csv(delegatecsv,index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True)
        if len(missedblockmsglist)>0:
            server = discord.utils.find(lambda m: (m.name).lower() == servername, list(bot.servers))
            userlist=server.members
            missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,discordnames,server)
            response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = 'No red nodes'
    for response in formatmsg(response,msglimit,'','','',''):
        await bot.say(response)

@bot.command(pass_context=True)
async def height(ctx,net='mainnet'):
    """Provides the current height accross mainnet or testnet nodes."""
    assert ctx.message.channel.name in channelnames
    assert net=='mainnet' or net=='testnet'
    if net=='testnet':
        connectedpeers,peerheight,consensus,backupheights=getstatus(testurl,testbackup,testport)
    else:
        connectedpeers,peerheight,consensus,backupheights=getstatus(url,backup,port)
    response=repr(backupheights)
    for response in formatmsg(response):
        await bot.say(response)

@bot.command(pass_context=True)
async def pools(ctx):
    """Returns the pools list."""
    assert ctx.message.channel.name in channelnames
    file= open(poolstxtfile,"r")
    response=file.read()
    file.close
    for response in formatmsg(response,msglimit,'','','',''):
        await bot.say(response)

@bot.command(pass_context=True)
async def forgingpools(ctx):
    """Returns the pools list filtered down to forging delegates."""
    assert ctx.message.channel.name in channelnames
    pools= getpools(poolstxtfile)
    delegates = pd.read_csv(delegatecsv,index_col=0)
    poolstats=getpoolstats(pools,delegates,numdelegates,blockrewards,blockspermin)
    response=printforgingpools(poolstats)
    for response in formatmsg(response,msglimit,'','','','',['\n']):
        await bot.say(response)

if __name__ == '__main__':
    bot.run(apitoken)

#!/usr/bin/env python3

from resources.functions import *

'''obtain config variables and initiate slack client'''
apitoken,url,backup,port,blockinterval,minmissedblocks,servername,channelnames,usernames,numdelegates,blockrewards,blockspermin,testurl,testbackup,testport,notificationmins,commandprefix=getconfigs('resources/config.json')
command=commandprefix
poolstxtfile="files/pools.txt"
delegatecsv="files/delegates.csv"
testdelegatecsv="files/testnet-delegates.csv"
discordnames=getusernames('resources/discordnames.json')
testdiscordnames=getusernames('resources/testnet-discordnames.json')
msglimit=1800
priceurl='https://api.coinmarketcap.com/v1/ticker/'

bot = commands.Bot(command_prefix=commands.when_mentioned_or(command))
bot.remove_command('help')

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    server = discord.utils.find(lambda m: (m.name).lower() == servername, list(bot.servers))
    print(server)
    print('------')

@bot.command(pass_context=True)
async def help(ctx):
    """Describes the bot and it's available commands."""
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
    commands = {command+'help':"Describes the bot and it's available commands.",
                command+'price (<coin name>) (<currency>)':'Retrieves price data for the specified coin. Defaults to LWF and USD.',
                command+'delegate (<username> or <rank>)':'Provides information of a delegate. Defaults to rank 201.',
                command+'rednodes (mainnet/testnet)':'Lists delegates that are currently missing blocks. Defaults to mainnet.',
                command+'height (mainnet/testnet)':'Provides the current height accross mainnet or testnet nodes. Defaults to mainnet.',
                command+'pools (list/forging/errors)':('Provides details about public sharing pools. Defaults to raw.'
                               '\n\t**raw** - Returns the entire sharing pool list with all details.'
                               '\n\t**list** - Returns a list of pools grouped by their sharing percentage.'
                               '\n\t**forging** - Returns the pools list filtered down to the current forging delegates.'
                               )

                }
    description='Available commands include:'
    embed=discordembeddict(commands,title=description,exclude=['?help'],inline=False)
    await bot.say(embed=embed)
    return

@bot.command(pass_context=True)
async def price(ctx,coin='local world forwarders',conv=''):
    """Retrieves price data for a specified coin. Ex: ?price bitcoin"""
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
    try:
        price,pricesummary=getprice(priceurl, coin, conv)
        embed=discordembeddict(pricesummary,['name','symbol','rank','market_cap USD'],pricesummary['name']+' ('+pricesummary['symbol']+')')
        #embed.set_image(url="https://cryptohistory.org/charts/light/"+pricesummary['symbol']+"-usd/7d/png")
        await bot.say(embed=embed)
    except:
        await bot.say('Command incorrect, try '+command+'price bitcoin')
        return

@bot.command(pass_context=True)
async def delegate(ctx,delegate='201',limit=3):
    """Filters the delegate list by name or rank. Ex: ?delegate deadpool"""
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
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
async def rednodes(ctx,net='mainnet'):
    """Lists delegates that are currently missing blocks."""
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
    try:
        assert net.lower()=='mainnet' or net.lower()=='testnet'
    except AssertionError:
        response = 'Network input incorrect. Should be "mainnet" or "testnet".'
        await bot.say(response)
        return
    if net.lower()=='testnet':
        delegates = pd.read_csv(testdelegatecsv,index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True,numdelegates)
        if len(missedblockmsglist)>0:
            server = discord.utils.find(lambda m: (m.name).lower() == servername, list(bot.servers))
            userlist=server.members
            missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,testdiscordnames,server)
            response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = 'No red nodes'
    else:
        delegates = pd.read_csv(delegatecsv,index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True,numdelegates)
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
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
    try:
        assert net.lower()=='mainnet' or net.lower()=='testnet'
    except AssertionError:
        response = 'Network input incorrect. Should be "mainnet" or "testnet".'
        await bot.say(response)
        return
    if net.lower()=='testnet':
        connectedpeers,peerheight,consensus,backupheights=getstatus(testurl,testbackup,testport)
    else:
        connectedpeers,peerheight,consensus,backupheights=getstatus(url,backup,port)
    response=repr(backupheights)
    for response in formatmsg(response):
        await bot.say(response)

@bot.command(pass_context=True)
async def pools(ctx,form='raw'):
    """Returns a list of delegates that share earnings to voters."""
    try:
        assert ctx.message.channel.name in channelnames
    except AssertionError:
        return
    validargs=['list','raw','forging','errors']
    try:
        assert form.lower() in validargs
    except AssertionError:
        response = 'Pool input incorrect. Should be "raw", "list", or "forging".'
        await bot.say(response)
        return
    if form.lower()=='raw':
        file= open(poolstxtfile,"r")
        response=file.read()
        file.close
        for response in formatmsg(response,msglimit,'','','',''):
            await bot.say(response)
    elif form.lower()=='list':
        pools,poolerrors= getpools(poolstxtfile)
        delegates = pd.read_csv(delegatecsv,index_col=0)
        poolstats=getpoolstats(pools,delegates,5000,blockrewards,blockspermin)
        response=printforgingpools(poolstats,5000)
        for response in formatmsg(response,msglimit,'','','','',['\n']):
            await bot.say(response)
    elif form.lower()=='forging':
        pools,poolerrors= getpools(poolstxtfile)
        delegates = pd.read_csv(delegatecsv,index_col=0)
        poolstats=getpoolstats(pools,delegates,numdelegates,blockrewards,blockspermin)
        response=printforgingpools(poolstats)
        for response in formatmsg(response,msglimit,'','','','',['\n']):
            await bot.say(response)
    elif form.lower()=='errors':
        pools,poolerrors= getpools(poolstxtfile)
        if len(poolerrors)>0:
            response=poolerrors.to_string(index=False)
        else:
            response='No errors'
        for response in formatmsg(response,msglimit,'','','','',['\n']):
            await bot.say(response)

async def price_loop():
    """Updates bot presence with current coin price."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    coin = 'bitcoin'
    price,pricesummary=getprice(priceurl, coin)
    last_price=-2
    while not bot.is_closed:
        price,pricesummary=getprice(priceurl, coin)
        if price != last_price:
            last_price = price
            rank=pricesummary['rank']
            change=pricesummary['Change 24h']
            change=change.replace(' :arrow_up_small:','')
            change=change.replace(' :arrow_down_small:','')
            await bot.change_presence(
                afk=True,
                status=discord.Status.invisible,
                game=discord.Game(name=pricesummary['symbol']+': '+price+' ('+change+')', type=3)
                )
        await asyncio.sleep(notificationmins*60)
        
async def mainnet_loop():
    """Updates the mainnet delegate list and notifies if delegates miss blocks."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    while not bot.is_closed:
        delegatesnew=getdelegates(url)
        try:
            delegates = pd.read_csv(delegatecsv,index_col=0)
        except FileNotFoundError:
            delegates=None
        delegates=processdelegates(delegatesnew,delegates)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,blockinterval,minmissedblocks,numdelegates=numdelegates)
        delegates.to_csv(delegatecsv)
        if len(missedblockmsglist)>0:
                discordnames=getusernames('resources/discordnames.json')
                server = discord.utils.find(lambda m: (m.name).lower() == servername, bot.servers)
                newmissedblockmsglist=modifymissedblockmsglist(missedblockmsglist,discordnames,server)
                message=makemissedblockmsg(newmissedblockmsglist,blockinterval)
                for channelname in channelnames:
                    await bot.send_message(getchannel(channelname,server), message)
                for username in usernames:
                    await bot.send_message(getuser(username,server), message)
        await asyncio.sleep(notificationmins*60)

async def testnet_loop():
    """Updates the testnet delegate list."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    while not bot.is_closed:
        testdelegatesnew=getdelegates(testurl)
        try:
            testdelegates = pd.read_csv(testdelegatecsv,index_col=0)
        except FileNotFoundError:
            testdelegates=None
        testdelegates=processdelegates(testdelegatesnew,testdelegates)
        testdelegates,testmissedblockmsglist=makemissedblockmsglist(testdelegates,blockinterval,minmissedblocks,numdelegates=numdelegates)
        testdelegates.to_csv(testdelegatecsv)
        await asyncio.sleep(notificationmins*60)

if __name__ == '__main__':
    bot.loop.create_task(price_loop())
    bot.loop.create_task(mainnet_loop())
    bot.loop.create_task(testnet_loop())
    bot.run(apitoken)

#!/usr/bin/env python3

'''Load Modules'''
import pandas as pd
import json
import sys
import discord
import logging
import asyncio
from discord.ext import commands

'''Load Functions'''
from functions.node import *
from functions.discordbot import *
from functions.notifications import *
from functions.responses import *

'''Load Configurations'''
try:
    discordconfigs=json.load(open('configs/discord.json','r'))
    mainnetconfigs=json.load(open('configs/mainnet.json','r'))
    testnetconfigs=json.load(open('configs/testnet.json','r'))
except:
	print ('Unable to load config files.')
	sys.exit ()

'''Setup Client'''
logging.basicConfig(level=logging.INFO)
bot = commands.Bot(command_prefix=commands.when_mentioned_or(discordconfigs.get("commandprefix")))
bot.remove_command('help')

@bot.event
async def on_ready():
    print('Logged in')
    print('Name: '+bot.user.name)
    print('ID: '+bot.user.id)
    server = discord.utils.find(lambda m: (m.name).lower() == discordconfigs.get("bot_server"), list(bot.servers))
    if server is None:
        print('Server: No Name')
    else:
        print('Server: '+server.name)
    print('------')

'''Define Bot Commands'''
@bot.command(pass_context=True)
async def help(ctx):
    """Describes the bot and it's available commands."""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    commands = {discordconfigs.get("commandprefix")+'help':"Describes the bot and it's available commands.",
                discordconfigs.get("commandprefix")+'info':"Useful resources. Try "+discordconfigs.get("commandprefix")+"info help",
                discordconfigs.get("commandprefix")+'price (<coin name>) (<currency>)':'Retrieves price data for the specified coin. Defaults to LWF and USD.',
                discordconfigs.get("commandprefix")+'delegate (<username> or <rank>)':'Provides information of a delegate. Defaults to rank 201.',
                discordconfigs.get("commandprefix")+'rednodes (mainnet/testnet)':'Lists delegates that are currently missing blocks. Defaults to mainnet.',
                discordconfigs.get("commandprefix")+'snapshot (mainnet/testnet)':'Show checksum for latest snapshot. Defaults to mainnet.',
                discordconfigs.get("commandprefix")+'height (mainnet/testnet)':'Provides the current height accross mainnet or testnet nodes. Defaults to mainnet.'#,
                #discordconfigs.get("commandprefix")+'pools':'Provides a list of pools and their details.'
                }
    description='Available commands include:'
    embed=discordembeddict(commands,title=description,exclude=[discordconfigs.get("commandprefix")+'help'],inline=False)
    await bot.say(embed=embed)
    return

@bot.command(pass_context=True)
async def info(ctx,subinfo='help'):
    """Useful resources."""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    allinfo=json.load(open('resources/info.json'))
    if subinfo.lower()=='help':
        helpinfo={}
        for key,value in allinfo.items():
            helpinfo[discordconfigs.get("commandprefix")+'info '+key]=allinfo[key]['help']
        description='Available info commands include:'
        embed=discordembeddict(helpinfo,title=description,exclude=['help'],inline=False)
        await bot.say(embed=embed)
    elif subinfo.lower() in allinfo:
        info=allinfo[subinfo.lower()]
        description=''
        embed=discordembeddict(info,title=description,exclude=['help'],inline=False)
        await bot.say(embed=embed)
    else:
        await bot.say('Information requested was not found. Check '+discordconfigs.get("commandprefix")+'info help')
        return
    return

@bot.command(pass_context=True)
async def price(ctx,coin='local world forwarders',conv=''):
    """Retrieves price data for a specified coin. Ex: ?price bitcoin"""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    try:
        price,pricesummary=getprice(discordconfigs.get("priceurl"), coin, conv)
        embed=discordembeddict(pricesummary,['name','symbol','rank','market_cap USD'],pricesummary['name']+' ('+pricesummary['symbol']+')')
        await bot.say(embed=embed)
    except:
        await bot.say('Command incorrect, try '+discordconfigs.get("commandprefix")+'price bitcoin')
        return

@bot.command(pass_context=True)
async def delegate(ctx,delegate='201',limit=3):
    """Filters the delegate list by name or rank. Ex: ?delegate deadpool"""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    delegates = pd.read_csv(mainnetconfigs.get("delegatecsv"),index_col=0)
    try:
        if delegate=='':
            response='Enter a delegate name or rank. Try '+discordconfigs.get("commandprefix")+'delegate 1'
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
        await bot.say('Not sure what you mean. Try '+discordconfigs.get("commandprefix")+'delegate 1')
        return
    for response in formatmsg(response,discordconfigs.get("msglenlimit"),'```','','\n','\n```',seps=['\n']):
        await bot.say(response)

@bot.command(pass_context=True)
async def rednodes(ctx,net='mainnet',ping="No"):
    """Lists delegates that are currently missing blocks."""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    try:
        assert net.lower()=='mainnet' or net.lower()=='testnet'
    except AssertionError:
        response = 'Network input incorrect. Should be "mainnet" or "testnet".'
        await bot.say(response)
        return
    if net.lower()=='testnet':
        delegates = pd.read_csv(testnetconfigs.get("delegatecsv"),index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True,discordconfigs.get("numdelegates"))
        if len(missedblockmsglist)>0:
            if ping.lower()=="ping":
                perms=ctx.message.author.roles
                perms=[i.name.lower() for i in perms]
                if any(x in perms for x in discordconfigs.get("elevatedperms")):
                    server = discord.utils.find(lambda m: (m.name).lower() == discordconfigs.get("bot_server"), list(bot.servers))
                    testnetdiscordnames=json.load(open('resources/testnet-discordnames.json'))
                    missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,testnetdiscordnames,server)
                    response=makemissedblockmsg(missedblockmsglist,0,True)
                else:
                    response='Invalid permissions'
            else:
                response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = 'No red nodes'
    else:
        delegates = pd.read_csv(mainnetconfigs.get("delegatecsv"),index_col=0)
        delegates,missedblockmsglist=makemissedblockmsglist(delegates,0,1,True,discordconfigs.get("numdelegates"))
        if len(missedblockmsglist)>0:
            if ping.lower()=="ping":
                perms=ctx.message.author.roles
                perms=[i.name.lower() for i in perms]
                print(perms)
                if any(x in perms for x in discordconfigs.get("elevatedperms")):
                    server = discord.utils.find(lambda m: (m.name).lower() == discordconfigs.get("bot_server"), list(bot.servers))
                    mainnetdiscordnames=json.load(open('resources/mainnet-discordnames.json'))
                    missedblockmsglist=modifymissedblockmsglist(missedblockmsglist,mainnetdiscordnames,server)
                    response=makemissedblockmsg(missedblockmsglist,0,True)
                else:
                    response='Invalid permissions'
            else:
                response=makemissedblockmsg(missedblockmsglist,0,True)
        else:
            response = 'No red nodes'
    for response in formatmsg(response,discordconfigs.get("msglenlimit"),'','','',''):
        await bot.say(response)

@bot.command(pass_context=True)
async def snapshot(ctx,net='mainnet'):
    """Show checksum for latest snapshot."""
    try:
        assert ctx.message.channel.name in discordconfigs.get("listen_channels")
    except AssertionError:
        return
    try:
        assert net.lower()=='mainnet' or net.lower()=='testnet'
    except AssertionError:
        response = 'Network input incorrect. Should be "mainnet" or "testnet".'
        await bot.say(response)
        return
    if net.lower()=='testnet':
        snapshoturl=testnetconfigs.get("snapshoturl")
    else:
        snapshoturl=mainnetconfigs.get("snapshoturl")
    try:
        checksum=getchecksum(snapshoturl)
        response=checksum
    except Exception as e:
        print(e)
        response='Could not get data from ' + snapshoturl
    for response in formatmsg(response,discordconfigs.get("msglenlimit")):
        await bot.say(response)

@bot.command(pass_context=True)
async def height(ctx,net='mainnet'):
    """Provides the current height accross mainnet or testnet nodes."""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.server is None)
    except AssertionError:
        return
    try:
        assert net.lower()=='mainnet' or net.lower()=='testnet'
    except AssertionError:
        response = 'Network input incorrect. Should be "mainnet" or "testnet".'
        await bot.say(response)
        return
    if net.lower()=='testnet':
        connectedpeers,peerheight,consensus,backupheights=getstatus(testnetconfigs.get("apinode"),testnetconfigs.get("corenodes"),testnetconfigs.get("port"))
    else:
        connectedpeers,peerheight,consensus,backupheights=getstatus(mainnetconfigs.get("apinode"),mainnetconfigs.get("corenodes"),mainnetconfigs.get("port"))
    response=repr(backupheights)
    for response in formatmsg(response,discordconfigs.get("msglenlimit")):
        await bot.say(response)
'''   
@bot.command(pass_context=True)
async def pools(ctx):
    """Provides the pools list."""
    try:
        assert (ctx.message.channel.name in discordconfigs.get("listen_channels")) or (ctx.message.channel.name in ['voters_channel']) or (ctx.message.server is None)
    except AssertionError:
        return
    try:
        req = requests.get(discordconfigs.get("poolsurl"))
        req.raise_for_status()
        response=req.text
    except Exception as e:
        print(e)
        response = 'Unable to read pools list from '+discordconfigs.get("poolsurl")
        await bot.say(response)
        return
    for response in formatmsg(response,discordconfigs.get("msglenlimit"),'','','',''):
        await bot.say(response)
'''
async def price_loop():
    """Updates bot presence with current coin price."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    coin = 'local-world-forwarders'
    price,pricesummary=getprice(discordconfigs.get("priceurl"), coin)
    last_price=-2
    while not bot.is_closed:
        try:
            price,pricesummary=getprice(discordconfigs.get("priceurl"), coin)
            if price != last_price:
                last_price = price
                rank=pricesummary['rank']
                change=pricesummary['Change 24h']
                change=change.replace(' :arrow_up_small:','')
                change=change.replace(' :arrow_down_small:','')
                await bot.change_presence(
                    afk=True,
                    status=discord.Status.online,
                    game=discord.Game(name=pricesummary['symbol']+': '+price+' ('+change+')', type=3)
                    )
        except Exception as e:
            print(e)
        await asyncio.sleep(discordconfigs.get("notificationmins")*60)

async def mainnet_loop():
    """Updates the mainnet delegate list and notifies if delegates miss blocks."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    while not bot.is_closed:
        try:
            delegatesnew=getdelegates(mainnetconfigs.get("apinode"))
            try:
                delegates = pd.read_csv(mainnetconfigs.get("delegatecsv"),index_col=0)
            except FileNotFoundError:
                delegates=None
            delegates=processdelegates(delegatesnew,delegates)
            delegates,missedblockmsglist=makemissedblockmsglist(delegates,discordconfigs.get("blockinterval"),discordconfigs.get("minmissedblocks"),numdelegates=discordconfigs.get("numdelegates"))
            delegates.to_csv(mainnetconfigs.get("delegatecsv"))
            if len(missedblockmsglist)>0 and len(mainnetconfigs.get("channels"))>0:
                    server = discord.utils.find(lambda m: (m.name).lower() == discordconfigs.get("bot_server"), bot.servers)
                    mainnetdiscordnames=json.load(open('resources/mainnet-discordnames.json'))
                    newmissedblockmsglist=modifymissedblockmsglist(missedblockmsglist,mainnetdiscordnames,server)
                    message=makemissedblockmsg(newmissedblockmsglist,discordconfigs.get("blockinterval"))
                    for channelname in mainnetconfigs.get("channels"):
                        await bot.send_message(getchannel(channelname,server), message)
        except Exception as e:
            print(e)
        await asyncio.sleep(discordconfigs.get("notificationmins")*60)

async def testnet_loop():
    """Updates the testnet delegate list."""
    await bot.wait_until_ready()
    await asyncio.sleep(1)
    while not bot.is_closed:
        try:
            testdelegatesnew=getdelegates(testnetconfigs.get("apinode"))
            try:
                testdelegates = pd.read_csv(testnetconfigs.get("delegatecsv"),index_col=0)
            except FileNotFoundError:
                testdelegates=None
            testdelegates=processdelegates(testdelegatesnew,testdelegates)
            testdelegates,testmissedblockmsglist=makemissedblockmsglist(testdelegates,discordconfigs.get("blockinterval"),discordconfigs.get("minmissedblocks"),numdelegates=discordconfigs.get("numdelegates"))
            testdelegates.to_csv(testnetconfigs.get("delegatecsv"))
            if len(testmissedblockmsglist)>0 and len(testnetconfigs.get("channels"))>0:
                    server = discord.utils.find(lambda m: (m.name).lower() == discordconfigs.get("bot_server"), bot.servers)
                    testnetdiscordnames=json.load(open('resources/testnet-discordnames.json'))
                    newtestmissedblockmsglist=modifymissedblockmsglist(testmissedblockmsglist,testnetdiscordnames,server)
                    message=makemissedblockmsg(newtestmissedblockmsglist,discordconfigs.get("blockinterval"))
                    for channelname in testnetconfigs.get("channels"):
                        await bot.send_message(getchannel(channelname,server), message)
        except Exception as e:
            print(e)
        await asyncio.sleep(discordconfigs.get("notificationmins")*60)

if __name__ == '__main__':
    bot.loop.create_task(price_loop())
    bot.loop.create_task(mainnet_loop())
    bot.loop.create_task(testnet_loop())
    bot.run(discordconfigs.get("apitoken"))

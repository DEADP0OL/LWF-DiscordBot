import discord

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
        for x in [v for v in userlist if (str(v.name).lower() in names) or (str(v.display_name).lower() in names)]:
            name='<@{}>'.format(str(x.id))
            display=x.name
        if str(display).lower()==delegate.lower():
            i["username"]=name + ' '
        else:
            i["username"]=delegate + ' ' + name + ' '
        newmissedblockmsglist.append(i)
    return newmissedblockmsglist

def checknames(name):
    """creates a list of delegate name variations to compare with slack/discord names"""
    names=[]
    names.append(name.lower())
    modifications={'_voting':'','_pool':'','s_pool':'','_delegate':''}
    for x,y in modifications.items():
        if x in name.lower():
            names.append(name.replace(x,y))
    return names

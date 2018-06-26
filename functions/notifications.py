import pandas as pd
import numpy as np

'''__________NOTIFICATION FUNCTIONS___________'''

def processdelegates(delegatesnew,delegates):
    """compares the current and previous delegate block counts to track consecutive missed/produced blocks"""
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
        delegatesnew['missedblocksmsg']=np.minimum(0,delegatesnew['missedblocksmsg']+delegatesnew['msgold'])
        delegatesnew['newmissedblocks']=np.minimum(0,delegatesnew['newmissedblocks']+delegatesnew['missedblocks']-delegatesnew['missedold'])
        #resets consecutive produced block counter to 0 if a delegate misses a block
        delegatesnew.loc[delegatesnew['missedblocks']-delegatesnew['missedold']>0, ['newproducedblocks']] = 0
        delegatesnew['newproducedblocks']=np.minimum(0,delegatesnew['newproducedblocks']+delegatesnew['producedblocks']-delegatesnew['producedold'])
        #resets consecutive missed block counter to 0 if a delegate produces a block
        delegatesnew.loc[delegatesnew['producedblocks']-delegatesnew['producedold']>0, ['newmissedblocks','missedblocksmsg']] = 0
        #resets all counters to 0 if a delegate begins forging
        delegatesnew.loc[delegatesnew['newmissedblocks'].isnull(), ['newmissedblocks','missedblocksmsg','newproducedblocks']] = 0
        #drops temporary columns
        delegatesnew=delegatesnew.drop(['missedold','producedold','msgold'],axis=1)
        return delegatesnew

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
import pandas as pd
import requests

'''__________RESPONSE FUNCTIONS___________'''

def printdelegates(delegates,rank,limit):
    """outputs the delegates list in a friendly format"""
    delegates=delegates.loc[(delegates['rank']>=rank-limit)&(delegates['rank']<=rank+limit)]
    delegates['voteweight'] = (delegates['vote']/1000).map('{:,.0f}'.format).astype(str) + 'K'
    delegates['productivity'] = delegates['productivity'].map('{:,.1f}%'.format)
    delegates['approval'] = delegates['approval'].map('{:,.2f}%'.format)
    ind=(delegates['rank'].values.tolist()).index(rank)
    delegates=insertblankrow(delegates,ind+1)
    cleandelegates=delegates[['rank','username','approval','voteweight','productivity']].to_string(index=False)
    return cleandelegates

def getprice(priceurl,coin,conv='',suffix='/'):
    """retrieves the price data for a specified coin"""
    coin=coin.replace(' ','-')
    if conv =='':
        url=priceurl+coin.lower()+suffix
        leaveout=['id','last_updated','max_supply','available_supply','total_supply']
    else:
        url=priceurl+coin.lower()+suffix+'?convert='+conv
        leaveout=['id','last_updated','max_supply','available_supply','total_supply','price USD','24h_volume USD','Change 1h','Change 24h','Change 7d']
    request=requests.get(url).json()
    data=request[0]
    data2=data.copy()
    for key,value in data2.items():
        if '_usd' in key:
            try:
                if float(value)>1000000:
                    data[key.replace('_usd',' USD')]="${:,.2f}MM".format(float(value)/1000000)
                elif float(value)>10000:
                    data[key.replace('_usd',' USD')]="${:,.2f}K".format(float(value)/1000)
                elif float(value)>1000:
                    data[key.replace('_usd',' USD')]="${:,.0f}".format(float(value))
                elif float(value)>1:
                    data[key.replace('_usd',' USD')]="${:,.2f}".format(float(value))
                elif float(value)>.1:
                    data[key.replace('_usd',' USD')]="${:,.3f}".format(float(value))
                elif float(value)>.01:
                    data[key.replace('_usd',' USD')]="${:,.4f}".format(float(value))
                else:
                    data[key.replace('_usd',' USD')]='$'+str(value)
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif '_btc' in key:
            try:
                if float(value)>10000:
                    data[key.replace('_btc',' BTC')]="{:,.2f}K BTC".format(float(value)/1000)
                elif float(value)>1000:
                    data[key.replace('_btc',' BTC')]="{:,.0f} BTC".format(float(value))
                else:
                    data[key.replace('_btc',' BTC')]="{:,.3f} BTC".format(float(value))
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif (conv.upper()!='BTC')and(conv!='')and('_'+conv.lower() in key):
            try:
                if float(value)>10000:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.2f}K".format(float(value)/1000)+' '+conv.upper()
                elif float(value)>1000:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.0f}".format(float(value))+' '+conv.upper()
                else:
                    data[key.replace('_'+conv.lower(),' '+conv.upper())]="{:,.3f}".format(float(value))+' '+conv.upper()
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
        elif 'percent_change_' in key:
            try:
                if float(value)>0:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))+' :arrow_up_small:'
                elif float(value)<0:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))+' :arrow_down_small:'
                else:
                    data[key.replace('percent_change_','Change ')]="{0:+.2f}%".format(float(value))
                leaveout.append(key)
            except:
                leaveout.append(key)
                pass
    if conv=='':
        price=data['price USD']
    elif conv.upper()!='BTC':
        field='price '+conv.upper()
        price=data[field]
        leaveout.append('price BTC')
    else:
        price=data['price BTC']
    for key in leaveout:
        data.pop(key, None)
    pricesummary=data
    return price,pricesummary

def insertblankrow(df,ind):
    """inserts a blank row into a dataframe at the specified index"""
    cols=list(df.columns.values)
    blank=pd.Series(['' for a in cols],index=cols)
    result=df.iloc[:ind].append(blank,ind)
    result=result.append(df.iloc[ind:],ind)
    return result

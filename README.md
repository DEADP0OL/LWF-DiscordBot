# DiscordBot API Scripts for Delegate and Voter Messages

A set of algorithms to analyze the LWF blockchain and provide Discord messages.

## Notifications

- Missed Blocks
- Wallet Offline (In Development)
- Network Consensus Below Threshold (In Development)

## Responses

- Blockchain metric responses
  - Block height, peers, consensus
  - Inactive "red" nodes
- Pools
- Enhanced pool list responses
  - Current rank 
  - Recent productivity (In Development)

## Installation

```git clone https://github.com/DEADP0OL/LWF-DiscordBot```

```cd LWF-DiscordBot```

```apt-get install python3-pip```

```pip3 install requests```

```pip3 install --user -U discord.py```

## Configuration

```nano resources/config.json```

- discordapitoken: The apitoken assigned to your bot
- apinode: The public node url or ip address for api requests (default https://wallet.lwf.io/)
- backupnodes: A list of nodes with api access to reach
- port: port number for api access
- blockintervalnotification: The number of consecutive blocks required to reissue a notifications
- minmissedblocks: The number of consecutive missed blocks required for an initial notification
- server: The discord server to use for notifications and responses
- channels: A list of channels to broadcast nofications on
- users: A list of users to send direct messages of notifications to
- numdelegates: The number of forging delegates on the blockchain
- blockrewards: The reward quantity for forging a block on the blockchain
- blockspermin: The number of blocks forged per a minute on the blockchain

## Activation

### Notifications

Notifications can be scheduled via crontab.

```crontab -e```

Add a line to run the notifications script regularly. The example below runs it every hour at the top of the hour.

```0 * * * * cd LWF-DiscordBot && python3 notifications.py && cd```

### Responses

Start the python script.

```cd LWF-DiscordBot```

```./lwfmain-bot.py```

To keep the python script running after closing the terminal run the following command.

```nohup ./lwfmain-bot.sh &```

To end the python script run the following command.

```pkill -f lwfmain-bot```

# DiscordBot API Scripts for Delegate and Voter Messages

A set of algorithms to analyze the LWF blockchain and provide Discord messages.

## Notifications

- Missed Blocks
- Wallet Offline (In Development)
- Potential Fork in a Core Node (In Development)
- Network Consensus Below Threshold (In Development)

## Responses

- **info** ([*subcommand*]) - Returns useful information.
- **price** ([*coin name*]) ([*currency*]) - Retrieves price data for the specified coin. Defaults to LWF and USD.
- **delegate** ([*username*] or [*rank*]) - Provides information of a delegate. Defaults to rank 201.
- **height** (*mainnet/testnet*) - Provides the current height accross mainnet or testnet nodes. Defaults to mainnet.
- **rednodes** (*mainnet/testnet*) - Lists delegates that are currently missing blocks. Defaults to mainnet.
- **pools** (*raw/list/forging*)- Provides details about public sharing pools. Defaults to raw.
  - *raw* - Pools list filtered to currently forging pools
  - *list* - Returns an list of pools grouped by their sharing percentage.
  - *forging* - Returns the pools list filtered down to the current forging delegates.

## Installation

```git clone https://github.com/DEADP0OL/LWF-DiscordBot```

```cd LWF-DiscordBot```

```apt-get install python3-pip```

```pip3 install requests```

```pip3 install --user -U discord.py```

## Configuration

```nano resources/config.json```

- **discordapitoken**: The apitoken assigned to your bot
- **apinode**: The public node url or ip address for api requests (default https://wallet.lwf.io/)
- **backupnodes**: A list of nodes with api access to monitor
- **port**: port number for api access
- **blockintervalnotification**: The number of consecutive blocks required to reissue a notifications
- **minmissedblocks**: The number of consecutive missed blocks required for an initial notification
- **numdelegates**: The number of forging delegates on the blockchain
- **blockrewards**: The reward quantity for forging a block on the blockchain
- **blockspermin**: The number of blocks forged per a minute on the blockchain
- **notificationmins**: The number of minutes to update delegate information for mainnet and testnet
- **commandprefix**: The character prefix for each bot function for the bot to listen for
- **server**: The discord server to use for notifications and responses
- **channels**: A list of channels to broadcast nofications on
- **users**: A list of users to send direct messages of notifications to
- **testapinode**: The public node url or ip address for api requests (default https://twallet.lwf.io/)
- **testbackupnodes**: A list of nodes with api access to monitor
- **testport**: port number for api access
- **testchannels**: A list of channels to broadcast testnet nofications on

## Activation

Start the python script.

```cd LWF-DiscordBot```

```./lwf-discordbot.py```

To keep the python script running after closing the terminal run the following command.

```nohup ./lwf-discordbot.sh &```

To end the python script run the following command.

```pkill -f lwf-discordbot```

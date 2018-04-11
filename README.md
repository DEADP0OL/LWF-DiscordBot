# Slackbot API Scripts for Delegate and Voter Notifications
A set of algorithms to anlayze the blockchain and provide Slack notifications.

## Scheduled Notifications

- Missed Blocks
- Wallet Offline (In Development)
- Consensus Below Threshold (In Development)

## Commands

- Blockchain metric responses
  - Block height, peers, consensus
  - Inactive "red" nodes
- Pools
- Enhanced pool list responses (In Development)
  - Current rank 
  - Recent productivity

## Installation

```git clone https://github.com/DEADP0OL/LWF-SlackBot```

```cd LWF-SlackBot```

```apt-get install python3-pip```

```pip3 install requests```

```pip3 install slackclient```

## Configuration

- slackapitoken: The apitoken assigned to your slackbot (ex: xoxb-############-###############)
- apinode: The public node url or ip address for api requests (default https://wallet.lwf.io/)
- missedblockinterval: The number of consecutive missed blocks required to reissue a slack alert
- minmissedblocks: The number of consecutive missed blocks required for an initial slack alert
- channels: A list of channels to broadcast nofications on
- users: A list of users to send direct messages of notifications to

## Activation

start the python script

```python3 slackbot.py```

or run the bash script to keep the python script running after closing the terminal

```nohup bash slackbot.sh &```

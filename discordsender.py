import requests

import config

def sendDiscord(toSend):
	def sendDiscordPart(partToSend):
		url = config.discordWebhookUrl
		data = {}
		data["username"] = "autodeploy"
		data["content"] = partToSend
		
		try:
			requests.post(url, json = data, headers={"Content-Type": "application/json"}, timeout = 30)
		except requests.exceptions.RequestException as e:
			print(f'send discord failed probably timeout {e}')

	toSend = str(toSend)
	
	for i in range(int(len(toSend) / 2000) + 1):
		sendDiscordPart(toSend[i * 2000:i* 2000 + 2000])
import os

deployedEventIds = []

def loadDeployedEventsFromFile():
	global deployedEventIds
	if os.path.exists('deployedevents.txt'):
		with open('deployedevents.txt', 'r') as sentIdsFile:
			deployedEventIds = sentIdsFile.read().splitlines()

def saveDeployedEventsToFile():
	global deployedEventIds
	with open('deployedevents.txt', 'w') as sentIdsFile:
		newStr = '\n'.join(deployedEventIds[-512:]) # 512 is more than enough
		sentIdsFile.write(newStr)

def eventDeployed(eventId):
	global deployedEventIds
	deployedEventIds.append(eventId)
	saveDeployedEventsToFile()

def alreadyDeployed(eventId):
	global deployedEventIds
	if eventId in deployedEventIds:
		return True
	return False

loadDeployedEventsFromFile()
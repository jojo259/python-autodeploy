import subprocess
import os
import time
import requests

import config

deployedEventIds = {}

newLineChar = '\n'

class Repo:
	def __init__(self, name, runCmd):
		self.name = name
		self.runCmd = runCmd

	def getWorkingDir(self):
		return f'../{self.name}'

	def getdeps(self):
		depsCommand = subprocess.Popen(['pip', 'install', '-r', 'requirements.txt'], cwd = self.getWorkingDir())
		depsCommand.wait()

	def pull(self):
		repoWorkingDir = self.getWorkingDir()
		if not os.path.isdir(repoWorkingDir): # if repo directory doesn't already exist then clone instead of pulling
			repoUrl = f'https://github.com/{config.githubUsername}/{self.name}'
			return subprocess.check_output(['git', 'clone', repoUrl], cwd = f'../').decode('UTF-8')
		return subprocess.check_output(['git', 'pull'], cwd = repoWorkingDir).decode('UTF-8')

	def run(self):
		runningRepos[curRepo.name] = subprocess.Popen(self.runCmd, cwd = self.getWorkingDir(), stdout = subprocess.DEVNULL, shell = True) # https://stackoverflow.com/questions/18962785/oserror-errno-2-no-such-file-or-directory-while-using-python-subprocess-wit

def sendDiscord(toSend):
	def sendDiscordPart(partToSend):
		url = config.discordWebhookUrl
		data = {}
		data["username"] = "autodeploy"
		data["content"] = partToSend
		
		try:
			requests.post(url, json = data, headers={"Content-Type": "application/json"}, timeout = 30)
		except requests.exceptions.RequestException as e:
			print('sender failed probably timeout')

	toSend = str(toSend)
	
	for i in range(int(len(toSend) / 2000) + 1):
		sendDiscordPart(toSend[i * 2000:i* 2000 + 2000])

if not os.path.exists('todeploy.txt'):
	with open('todeploy.txt', 'w') as toDeployFile:
		toDeployFile.write('repo-name,run command')
	print('no todeploy.txt config file found. generated todeploy.txt\nplease edit and re-run program\nexiting')
	exit()

reposToDeploy = {}

with open('todeploy.txt', 'r') as toDeployFile:
	reposData = toDeployFile.read().splitlines()
	for curRepoData in reposData:
		curRepoDataSplit = curRepoData.split(',')
		reposToDeploy[curRepoDataSplit[0]] = Repo(curRepoDataSplit[0], curRepoDataSplit[1])

print(f'running {len(reposToDeploy)} repos')

runningRepos = {}

for curRepoName, curRepo in reposToDeploy.items():
	print(f'pulling {curRepo.name}')
	print(curRepo.pull())
	print(f'installing dependencies for {curRepo.name}')
	curRepo.getdeps()
	print(f'running {curRepo.name}')
	curRepo.run()

print('ran repos')

while True:
	time.sleep(60)
	print('checking for deploy updates')

	reqHeaders = {'Authorization': f'token {config.githubToken}'}
	eventsApi = requests.get(f'https://api.github.com/users/{config.githubUsername}/events', headers = reqHeaders, timeout = 30).json()

	for curEvent in list(reversed(eventsApi))[-5:]:
		if curEvent.get('id', '') in deployedEventIds:
			continue

		if curEvent.get('type') != 'PushEvent':
			continue

		repoName = curEvent.get('repo', {}).get('name', '').split("/")[1]

		if repoName not in runningRepos:
			continue

		deployedEventIds[curEvent.get('id', '')] = True

		allCommits = []

		for curCommit in curEvent.get('payload', {}).get('commits', []):
			allCommits.append(' - ' + curCommit.get('message'))

		commitsStr = '\n' + '\n'.join(allCommits)

		logPre = f'git push detected for {repoName} at {curEvent.get("created_at", "[error: no time]")}: {commitsStr}'

		print(logPre)
		sendDiscord(f'```{logPre}```')

		gitPulled = reposToDeploy[repoName].pull()

		logPost = f'git push for {repoName} at {curEvent.get("created_at", "[error: no time]")}, git pull output:{newLineChar}{gitPulled}'

		print(logPost)
		sendDiscord(f'```{logPost}```')

		curRepo.getdeps()

		runningRepos[repoName].kill()
		reposToDeploy[repoName].run()
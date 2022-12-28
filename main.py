import subprocess
import os
import time
import requests
import signal
import zipfile
import shutil

import config
import discordsender
import deployedeventstorer

class Repo:
	def __init__(self, name, runCmd):
		self.name = name
		self.runCmd = runCmd

	def getWorkingDir(self):
		return 'temp/workingrepos/' + self.name + '/' + os.listdir(f'temp/workingrepos/{self.name}/')[0]

	def getDeps(self):
		depsCommand = subprocess.Popen(['pip', 'install', '-r', 'requirements.txt'], cwd = self.getWorkingDir())
		depsCommand.wait()

	def pull(self):
		gotRepo = requests.get(f'https://api.github.com/repos/{githubUsername}/{self.name}/zipball', headers = authorizationHeaders)

		downloadPath = f'temp/repozips/{self.name}'
		extractPath = f'temp/workingrepos/{self.name}'

		# delete old workingrepo

		if os.path.exists(extractPath):
			shutil.rmtree(extractPath)

		# download repo zip file

		with open(downloadPath, 'wb') as downloadedZip:
			downloadedZip.write(gotRepo.content)

		# unzip

		with zipfile.ZipFile(downloadPath, 'r') as toUnzip:
			toUnzip.extractall(extractPath)

		# add .env file

		envFilePath = f'envfiles/{self.name}.env'
		if os.path.exists(envFilePath):
			shutil.copy(envFilePath, self.getWorkingDir() + '/.env')

	def run(self):
		runningRepos[curRepo.name] = subprocess.Popen(self.runCmd.split(' '), cwd = self.getWorkingDir()) # https://stackoverflow.com/questions/18962785/oserror-errno-2-no-such-file-or-directory-while-using-python-subprocess-wit

def createDirIfNotExist(dirPath):
	if not os.path.exists(dirPath):
		os.makedirs(dirPath)

def printAndSendDiscord(printStr):
	print(printStr)
	if config.discordWebhookUrl != None and config.discordWebhookUrl != '':
		discordsender.sendDiscord(f'```{printStr}```')

authorizationHeaders = {'Authorization': f'token {config.githubToken}'}

# get GitHub username

userApiGot = requests.get('https://api.github.com/user', headers = authorizationHeaders).json()
githubUsername = userApiGot['login']

# create directory to hold .env files if doesn't exist and todeploy.txt file

createDirIfNotExist('envfiles')

if not os.path.exists('todeploy.txt'):
	with open('todeploy.txt', 'w') as toDeployFile:
		toDeployFile.write('repo-name,run command')
	print('no todeploy.txt config file found. generated todeploy.txt\nplease edit and re-run program\nexiting')
	exit()

discordsender.sendDiscord(f'```autodeploy init```')

# delete old temp directory if exists

if os.path.exists('temp'):
	shutil.rmtree('temp')

# create temp directory to hold repo files

createDirIfNotExist('temp')
createDirIfNotExist('temp/repozips')
createDirIfNotExist('temp/workingrepos')

reposToDeploy = {}

with open('todeploy.txt', 'r') as toDeployFile:
	reposData = toDeployFile.read().splitlines()
	for curRepoData in reposData:
		curRepoDataSplit = curRepoData.split(',')
		reposToDeploy[curRepoDataSplit[0]] = Repo(curRepoDataSplit[0], curRepoDataSplit[1])

printAndSendDiscord(f'running {len(reposToDeploy)} repos')

runningRepos = {}

for curRepoName, curRepo in reposToDeploy.items():

	printAndSendDiscord(f'pulling repo {curRepo.name}')
	curRepo.pull()

	printAndSendDiscord(f'installing dependencies for repo {curRepo.name}')
	curRepo.getDeps()

	printAndSendDiscord(f'running repo {curRepo.name}')
	curRepo.run()

printAndSendDiscord(f'autodeploy starting')

def doLoop():
	try:

		time.sleep(60)

		# check if any processes have terminated

		for curRepoName, curRepo in runningRepos.items():

			if curRepo.poll() != None:

				# process has terminated, restart it

				print(f'process terminated: {curRepoName}')
				reposToDeploy[curRepoName].run()

		# check for pushes

		try:
			eventsApi = requests.get(f'https://api.github.com/users/{githubUsername}/events', headers = authorizationHeaders, timeout = 30).json()
		except Exception as e:
			print(f'get api failed {e}')
			return

		for curEvent in list(reversed(eventsApi))[-64:]:
			if curEvent.get('type') != 'PushEvent':
				continue

			if deployedeventstorer.alreadyDeployed(curEvent.get('id', '')):
				continue

			repoName = curEvent.get('repo', {}).get('name', '').split("/")[1]

			if repoName not in runningRepos:
				continue

			allCommits = []

			for curCommit in curEvent.get('payload', {}).get('commits', []):
				allCommits.append(' - ' + curCommit.get('message'))

			commitsStr = '\n' + '\n'.join(allCommits)

			logStr = f'git push detected for {repoName} at {curEvent.get("created_at", "[error: no time]")}: {commitsStr}'

			printAndSendDiscord(logStr)

			gitPulled = reposToDeploy[repoName].pull()

			reposToDeploy[repoName].getDeps()

			runningRepos[repoName].kill()
			reposToDeploy[repoName].run()

			deployedeventstorer.eventDeployed(curEvent.get('id', ''))

	except Exception as e:
		printAndSendDiscord(f'doLoop errored: {e}')

while True:
	doLoop()
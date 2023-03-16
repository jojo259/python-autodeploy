import subprocess
import os
import time
import requests
import signal
import zipfile
import shutil
import traceback

import config
import discordsender
import deployedeventstorer

class Repo:
	def __init__(self, owner, name, runCmd):
		self.owner = owner
		self.name = name
		self.runCmd = runCmd
		self.runningRepo = None

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
		self.runningRepo = subprocess.Popen(self.runCmd.split(' '), cwd = self.getWorkingDir()) # https://stackoverflow.com/questions/18962785/oserror-errno-2-no-such-file-or-directory-while-using-python-subprocess-wit

	def checkForNewCommit(self):
		commitsApi = requests.get(f'https://api.github.com/repos/{githubUsername}/{self.name}/commits', headers = authorizationHeaders, timeout = 30).json()

		for curCommit in list(reversed(commitsApi))[:64]:

			commitSha = curCommit['sha']

			if deployedeventstorer.alreadyDeployed(commitSha):
				continue

			commitMessage = curCommit['commit']['message']
			commitTime = curCommit['commit']['committer']['date']

			printAndSendDiscord(f'pulling commit detected for repo {self.name} at {commitTime}: {commitMessage}')

			self.runningRepo.kill()

			gitPulled = self.pull()

			printAndSendDiscord(f'installing dependencies for repo {self.name}')
			self.getDeps()

			printAndSendDiscord(f'running new process for repo {self.name}')
			self.run()

			deployedeventstorer.eventDeployed(commitSha)

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
		toDeployFile.write('repo-owner/repo-name,run command')
	printAndSendDiscord('no todeploy.txt config file found. generated todeploy.txt\nplease edit and re-run program\nexiting')
	exit()

printAndSendDiscord(f'autodeploy init')

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
		curRepoOwnerNameSplit = curRepoDataSplit[0].split('/')
		reposToDeploy[curRepoDataSplit[0]] = Repo(curRepoOwnerNameSplit[0], curRepoOwnerNameSplit[1], curRepoDataSplit[1])

printAndSendDiscord(f'running {len(reposToDeploy)} repos')

for curRepoName, curRepo in reposToDeploy.items():

	printAndSendDiscord(f'pulling repo {curRepo.name}')
	curRepo.pull()

	printAndSendDiscord(f'installing dependencies for repo {curRepo.name}')
	curRepo.getDeps()

	printAndSendDiscord(f'running repo {curRepo.name}')
	curRepo.run()

printAndSendDiscord(f'autodeploy starting')

def doLoop():

	time.sleep(60)

	print('doing main loop')

	# check if any processes have terminated

	for curRepoName, curRepo in reposToDeploy.items():
		if curRepo.runningRepo != None:
			repoPollCode = curRepo.runningRepo.poll()
			if repoPollCode != None:
				# process has terminated, restart it
				printAndSendDiscord(f'process {curRepoName} terminated with poll code {pollCode}')
				reposToDeploy[curRepoName].run()

	# check for pushes from each repo

	for curRepoName, curRepo in reposToDeploy.items():
		curRepo.checkForNewCommit()

while True:
	try:
		doLoop()
	except Exception as e:
		stackTraceStr = traceback.format_exc()
		printAndSendDiscord(f'doLoop errored:\n{stackTraceStr}')
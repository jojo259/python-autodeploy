import os

import dotenv

dotenvValues = dotenv.dotenv_values(".env") # can't use load_dotenv or environment variables will be passed to subprocesses

githubToken = dotenvValues['githubaccesstoken']
githubUsername = dotenvValues['githubusername']
discordWebhookUrl = dotenvValues['discordwebhookurl']
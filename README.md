# Python Autodeployer

## Functionality

Deploys GitHub repositories + detects and automatically deploys new pushes. Restarts process upon error.

## Setup

Clone repository and copy/rename `.env.example` to `.env` and add a [GitHub access token](https://github.com/settings/tokens) and a Discord webhook URL to see logs from the autodeployer (optional, can be left blank).

Create a file called `todeploy.txt` and enter the repositories you wish to deploy in the format `repo-name,run command` on each line. `repo-name` is the repository's name e.g. `python-autodeploy` and `run command` is the command to run it e.g. `python main.py`.

If any of your repositories require `.env` files for environment variables then create a directory called `envfiles` and place the `.env` files in there, renamed to `repo-name.env`, e.g. `python-autodeploy.env`. They will be moved into the repository's working directory upon running and renamed to `.env`.

## Not supported

- Non-Python projects because it always runs the command `pip install -r requirements.txt`
- Projects with conflicting dependencies because it doesn't use virtual environments
- Projects with identical names (from different users)

## To-do

Fix all of the above
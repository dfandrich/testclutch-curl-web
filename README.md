# Test Clutch deployment for curl

This repository contains the files needed to deploy an instance of [Test
Clutch](https://github.com/dfandrich/testclutch/) customized for the curl
project to a host running Virtuozzo Application Platform cloud service.

# Installation

The latest source can be obtained from
https://github.com/dfandrich/testclutch-curl-web/

The build scripts require Python 3 (ver. 3.9 or higher) with the `pip` package,
as well as `git` and `xz`.

Run `./builddeployment` to create `testclutch_deploy.tar.xz`, a deployment
bundle that contains the static web content, Python source code as well as all
the necessary Test Clutch source code and dependencies. The script assumes the
testclutch source is in the directory `../testclutch/` and the `master` branch
is the version to deploy. To change these, run the script with two arguments of
branch or tag and git repository location (local or remote), respectively.

The exact Python dependency versions to use are found in the file
requirements-testclutch.txt.

The script writes the files `testclutch_deploy-commit.txt`,
`testclutch_deploy-requirements.txt` and `testclutch_deploy-tag.txt` which
contain the commit ID of the testclutch source, the Python modules and their
versions used, and the latest tag in the git repository, respectively.

# Environment Setup

The deployment bundle is designed to be deployed on Virtuozzo Application
Platform (formerly Jelastic), a container orchestration service. Create a new
environment from scratch by following these steps:

0. Choose *NEW ENVIRONMENT*
0. At the top of the environment topology diagram, click *SSL* and *enable wildcard SSL*
0. in the *Application* block, choose *Apache Python*
    - tested version: Apache 2.4.63
    - tested version: Python 3.12.10
    - tested version: Almalinux 9
0. Under *Application Servers*:
    - 1 reserved cloudlet, 1 scaling limit, 1 horizontal scaling
    - horizontal scaling: stateless
    - disk limit 5 GB
    - access via SLB: ON
    - Public IPv4: OFF
    - Environment Name: &lt;unique hostname>
0. In the *Storage Containers* block, choose *Shared Storage*
    - tested version: NFS 2.0-10.5-almalinux-9
    - 1 reserved cloudlet, 1 scaling limit, 1 horizontal scaling
    - horizontal scaling: stateless
    - auto-clustering: OFF
    - access via SLB: OFF
    - disk limit 40 GB
0. In *Application Servers*, *Settings→Volumes*
    - Choose Add, Data Container, Shared Storage node, click checkbox for
      `/data /data`, then *Add*, *Apply*
0. In *<your environment>*, *Settings→Load Alerts*
    - Change the *auto_alert_cpu* threshold to 99% and duration to 60 minutes
      (the batch jobs are expected to run with 100% CPU for some time)
    - Change the *auto_alert_disk* threshold to 95%.

# Deployment

In the *Deployment Manager*, upload `testclutch_deploy.tar.xz` and choose the
*Deploy to...* option to deploy to the application server just created. Set the
*Post deploy* hook to:
```sh
#!/bin/bash
exec /var/www/webroot/ROOT/application/bin/post-deploy
```

# Redeployment

To update Test Clutch, just upload a new bundle and deploy it as before. The
*Post deploy* hook should already be set as above.

When using the *Redeploy* option to update the application servers, ensure
that *Keep volume data* is ON. If redeployment happens with that off, the
application code will be gone and there will be a site outage until you deploy
a bundle again. Once the redeployment completes, log in via ssh and manually
run the post deploy script */var/www/webroot/ROOT/application/bin/post-deploy*.
This is necessary because the crontab file is not preserved over the
redeployment. Instead of manually running the post deploy script like this, you
can instead deploy a new (or old) application version (under the *Deployment*
section above) which will run the post deploy script for you.

Also, remember to download any needed journal logs first as they will be lost
during redeployment.

# Tokens

GitHub requires an access token for Test Clutch to download GitHub Actions
logs and to comment on pull requests. Create one by going to
https://github.com/settings/tokens and choosing a Classic token with the
`public_repo` scope enabled. This can be done by any GitHub user, including the
`testclutch` robot user.

When running as a user who is an owner of the curl repository, a fine-grained
token is preferred.  Create a token with these characteristics:

  * Resource owner (select curl)
  * Only select repositories (selecting the source repository or repositories)
  * "Metadata" repository permissions (read)
  * "Pull requests" repository permissions (read and write)

Either way, copy the token contents from the web browser and store it in a file
called `ghatoken` in a protected location on your local machine. Use the
*Application Servers - Config* menu in Virtuozzo to upload that file to the
container in the location `/data/auth/ghatoken`. Once the file is there, the
periodic update job will start downloading GitHub Actions logs on its next run.

# Logs

Application logs are stored in the journal and may be downloaded using the
*Application Servers: Log* menu. Navigate to `/journal/X` (where `X` is a
unique identifier) and download the journal files desired. The files are
automatically rotated.

Job run times can be extracted from these journals with a command like:
```sh
scripts/collect-process-durations.py system*.journal | sort -n > times.csv
```
The extracted times can be plotted using gnuplot with:
```sh
scripts/plot-job-times times.csv
```
If some interim partial log files were downloaded before the completed,
rotated ones were ready, the partial ones can be deleted with the command:
```sh
scripts/delete-subset-logs system*.journal
```
to avoid duplicated data points.  The modification times of the log files must
remain accurate to the times of the last log message or else an incorrect log
file could be deleted by this script by mistake (a full one could be deleted
instead of the matching partial one). The author's program `automtime`
(available as part of
[fileviewinfo](https://github.com/dfandrich/fileviewinfo)) can be used to set
the times correctly before the delete script is run, if in doubt. This can
most commonly be an issue if a partial log file is downloaded before an older,
rotated one.

## Author

Copyright (c) 2024-2025 Dan Fandrich <dan@coneharvesters.com>
Licensed under the MIT license (see the file [LICENSE](LICENSE) for details)

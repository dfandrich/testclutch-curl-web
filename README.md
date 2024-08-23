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

The script writes the files `testclutch_deploy-commit.txt` and
`testclutch_deploy-requirements.txt` which contain the commit ID of the
testclutch source and the Python modules and their versions used, respectively.

# Environment Setup

The deployment bundle is designed to be deployed on Virtuozzo Application
Platform (formerly Jelastic), a container orchestration service. Create a new
environment from scratch by following these steps:

0. Choose *NEW ENVIRONMENT*
0. At the top of the environment topology diagram, click *SSL* and *enable wildcard SSL*
0. in the *Application* block, choose *Apache Python*
    - tested version: Apache 2.4.62
    - tested version: Python 3.11.9
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
    - disk limit 25 GB
0. In *Application Servers*, *Settings→Volumes*
    - Choose Add, Data Container, Shared Storage node, click checkbox for
      `/data /data`, then *Add*, *Apply*
0. In *<your environment>*, *Settings→Load Alerts*
    - Change the *auto_alert_cpu* threshold to 90%.

# Deployment

In the *Deployment Manager*, upload `testclutch_deploy.tar.xz` and choose the
*Deploy to...* option to deploy to the application server just created. Set the
*Post deploy* hook to:
```sh
#!/bin/bash
exec /var/www/webroot/ROOT/application/bin/post-deploy
```

# Redeployment

To update the software, just upload a new bundle and deploy it as before. The
*Post deploy* hook should remain the same as before.

When using the *Redeploy* option to updates the application servers, ensure
that *Keep volume data* is ON. If redeployment happens with that off, the
application code will be gone and there will be a site outage until you deploy
a bundle again. Once the redeployment completes, log in via ssh and manually
run the post deploy script */var/www/webroot/ROOT/application/bin/post-deploy*.
This is necessary because the crontab file is not preserved over the
redeployment.

# Tokens

GitHub requires an access token for Test Clutch to download GitHub Actions
logs. Create one by going to https://github.com/settings/tokens and choosing
fine-grained tokens. Create a new token with these characteristics:

  - Public repository access (no other special fine-grained access is needed)

Copy the token contents from the web browser and store it in a file called
`ghatoken` in a protected location on your local machine. Use the *Application
Servers - Config* menu in Virtuozzo to upload that file to the container in the
location `/data/auth/ghatoken`. Once the file is there, the periodic update job
will start downloading GitHub Actions logs on its next run.

# Logs

Application logs are stored in the journal and may be downloaded using the
*Application Servers: Log* menu. Navigate to `/journal/X` (where `X` is a
unique identifier) and download the journal files desired. The files are
automatically rotated.

## Author

Copyright (c) 2024 Dan Fandrich <dan@coneharvesters.com>
Licensed under the MIT license (see the file [LICENSE](LICENSE) for details)

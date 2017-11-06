from __future__ import with_statement

import re

from fabric.api import *
from fabric.colors import *

LATENCY_RPM_URL = 'http://cdn.cavaliercoder.com/LatencyConf2017/latencyd-1.0.0-1.el7.x86_64.rpm'

def get_instanceid():
    """
    Return the Instance ID of the current host.
    """
    return run('curl -s http://169.254.169.254/latest/meta-data/instance-id',
               quiet=True)

@task
def get_instances(environment, user='centos'):
    """
    Searches EC2 for Instances matching the given 'Environment' tags values.
    Discovered Instances are added to env.hosts for use in subsequent tasks.
    """

    from boto3 import client
    ec2 = client('ec2')
    res = ec2.describe_instances(Filters=[
        {'Name': 'tag:Environment', 'Values': [environment]},
        {'Name': 'instance-state-name', 'Values': ['running']},
    ])
    count = 0
    for reservation in res['Reservations']:
        for instance in reservation['Instances']:
            env.hosts.append('%s@%s' % (user, instance['PublicIpAddress']))
            count += 1
    if count == 0:
        print(red('No EC2 Instances found where Environment=%s' % environment))
        return
    print(green('Found %d EC2 Instances where Environment=%s' % (count, environment)))
    

@parallel
def install_latencyd():
    res = run('/bin/sudo -n /usr/bin/rpm -q latencyd', warn_only=True)
    if res.return_code != 0:
        run('/bin/sudo -n /usr/bin/yum install %s' % LATENCY_RPM_URL)
    run('/bin/sudo -n /bin/systemctl enable latencyd')

@parallel
def restart_latencyd():
    """
    TODO
    """

    run('/bin/sudo -n /bin/systemctl restart latencyd')

@task
def deploy():
    """
    TODO
    """

    execute(get_instances, 'demo')
    execute(install_latencyd)
    execute(restart_latencyd)

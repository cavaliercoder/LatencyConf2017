from __future__ import with_statement

import re

from fabric.api import *
from fabric.colors import *

from pydot import graph_from_dot_file

ENVIRONMENT = 'latency-demo'
LATENCY_RPM_URL = 'http://s3.cavaliercoder.com/LatencyConf2017/latencyd-1.0.0-1.el7.x86_64.rpm'

def get_instanceid():
    """
    Return the Instance ID of the current host.
    """
    return run('curl -s http://169.254.169.254/latest/meta-data/instance-id',
               quiet=True)

def get_tag(instance, key, default=None):
    for tag in instance['Tags']:
        if tag['Key'] == key:
            return tag['Value']
    return default

def build_latencyd_configs():
    g = graph_from_dot_file('webapp.dot')[0]
    env.configs = {}
    for host in env.mappings: # BUG: includes IP addresses
        name = env.mappings[host] # e.g. "node1"
        nodes = g.get_node(name)
        if not nodes:
            continue
        n = nodes[0]
        config = {
            'nodeName': n.get('label').strip('"') or 'Unknown',
            'listenAddr': ':3000',
            'latency': int(n.get('latency')),
            'variance': 0.3,
            'logFile': '/var/log/latencyd/latencyd.log',
            'backends': [],
        }
        for e in g.get_edges():
            if e.get_source() != name:
                continue
            dst = e.get_destination()
            dnodes = g.get_node(dst)
            if not dnodes:
                continue
            config['backends'].append({
                'name': dnodes[0].get('label').strip('"') or dst,
                'url': 'http://%s:3000/' % env.mappings.get(dst),
                'timeout': int(e.get('timeout')),
            })
        env.configs[host] = config

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
    env.mappings = {}
    for reservation in res['Reservations']:
        for instance in reservation['Instances']:
            env.hosts.append('%s@%s' % (user, instance['PublicIpAddress']))
            name = get_tag(instance, 'Name', 'Unknown')
            env.mappings[instance['PublicIpAddress']] = name
            env.mappings[name] = instance['PublicIpAddress']
            count += 1
    build_latencyd_configs()
    if count == 0:
        print(red('No EC2 Instances found where Environment=%s' % environment))
        return
    print(green('Found %d EC2 Instances where Environment=%s' % (count, environment)))

@parallel
def install_latencyd():
    res = run('/usr/bin/rpm -q latencyd', warn_only=True, quiet=True)
    if res.return_code != 0:
        sudo('/usr/bin/yum -y -q -e 0 install %s' % LATENCY_RPM_URL)
    sudo('/bin/systemctl enable latencyd')

@parallel
def configure_latencyd():
    from json import dumps
    from StringIO import StringIO

    if env.host not in env.configs:
        abort('no configuration found for instance: %s' % env.host)
    config = StringIO(dumps(env.configs[env.host], indent=2))
    put(config, '/etc/latencyd/config.json', use_sudo=True)
    sudo('/bin/systemctl restart latencyd')

@parallel
def uninstall_latencyd():
    sudo('/usr/bin/yum -y -q -e 0 remove latencyd')


@task
def setup():
    execute(get_instances, ENVIRONMENT)
    execute(install_latencyd)
    execute(configure_latencyd)

@task
def deploy():
    execute(get_instances, ENVIRONMENT)
    execute(configure_latencyd)

@task
def destroy():
    execute(get_instances, ENVIRONMENT)
    execute(uninstall_latencyd)

from __future__ import with_statement

import re

from shutil import copyfile

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

def build_latencyd_configs(graph):
    """
    Build latencyd configurations using the given graphviz dot file.
    Resultant configurations are stored in env.configs keyed by IP address.
    """

    g = graph_from_dot_file('../slides/%s.dot' % graph)[0]
    env.configs = {}
    for host in env.mappings: # BUG: env.mappings also contains reverse mappings
        name = env.mappings[host] # e.g. name = "node1"
        config = {
            'nodeName': name,
            'listenAddr': ':3000',
            'load': 0,
            'variance': 0.3,
            'logFile': '/var/log/latencyd/latencyd.log',
            'backends': [],
        }
        nodes = g.get_node(name)
        if nodes:
            n = nodes[0]
            config['nodeName'] = n.get('label').strip('"') or host
            config['load'] = int(n.get('load') or '1')
            for e in g.get_edges():
                if e.get_source() != name:
                    continue
                dst = e.get_destination()
                dnodes = g.get_node(dst)
                if not dnodes:
                    continue
                config['backends'].append({
                    'name': dnodes[0].get('label').strip('"') or dst,
                    'url': 'http://%s:3000/' % env.mappings.get(dst), # BUG: unhandled error case
                    'timeout': int(e.get('timeout') or '0'),
                    'roundtrips': int(e.get('roundtrips') or '1'),
                })
        env.configs[host] = config

@task
def get_instances(environment, user='centos', graph=None):
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
    if graph:
        build_latencyd_configs(graph)
    if count == 0:
        print(red('No EC2 Instances found where Environment=%s' % environment))
        return
    print(green('Found %d EC2 Instances where Environment=%s' % (count, environment)))

@parallel
def install_latencyd():
    # install ab, jq
    sudo('/usr/bin/yum -y -q -e 0 install epel-release')
    sudo('/usr/bin/yum -y -q -e 0 install httpd-tools jq')

    # install latencyd from rpm url
    res = run('/usr/bin/rpm -q latencyd', warn_only=True, quiet=True)
    if res.return_code != 0:
        sudo('/usr/bin/yum -y -q -e 0 install %s' % LATENCY_RPM_URL)
    sudo('/bin/systemctl enable latencyd')

@parallel
def configure_latencyd():
    from json import dumps
    from StringIO import StringIO

    if 'configs' not in env:
        abort('no latencyd configurations found')
    if env.host not in env.configs:
        abort('no latencyd configuration found for instance: %s' % env.host)
    config = StringIO(dumps(env.configs[env.host], indent=2))
    put(config, '/etc/latencyd/config.json', use_sudo=True)
    sudo('/bin/systemctl restart latencyd')
    print(green('Configured %s (%s) as %s' % (
        env.mappings[env.host],
        env.host,
        env.configs[env.host]['nodeName'])))

@task
def bench(concurrency=1, duration=5):
    keepers = (
        'Complete requests:',
        'Non-2xx responses:',
        'Requests per second:',
        'Time per request:',
        'Percentage of the requests',
        '  50%',
        ' 100%',
    )
    cmd = '/usr/bin/ab -t%s -c%s http://localhost:3000/' % (duration, concurrency)
    res = run(cmd, quiet=True)

    # write raw output
    f = open('./ab.out', 'w')
    f.write(res)
    f.close()

    if res.return_code != 0:
        copyfile('./ab.out', './ab.sample')
        return

    # write sampled output
    lines = res.splitlines()
    lines = lines[15:] # drop headers
    f = open('./ab.sample', 'w')
    f.write('$ %s\n\n' % cmd)
    skipped = 0
    for line in lines:
        keep = False
        for keeper in keepers: # O(n2) yikes
            if line.startswith(keeper):
                keep = True
        if keep:
            skipped = 0
            f.write(line + '\n')
        else:
            skipped += 1
        if skipped == 1:
            f.write('...\n')
    f.close()

@parallel
def uninstall_latencyd():
    """
    Uninstall latencyd from the target host.
    """

    sudo('/usr/bin/yum -y -q -e 0 remove latencyd')


@task
def setup():
    """
    Install and enable latencyd.
    """

    execute(get_instances, ENVIRONMENT)
    execute(install_latencyd)

@task
def deploy(graph):
    """
    Build latencyd configurations from the given dot graph file and deploy the configurations to
    EC2 Instances.
    """

    execute(get_instances, ENVIRONMENT, graph=graph)
    execute(configure_latencyd)

@task
def destroy():
    """
    Uninstall latencyd from all target EC2 instances.
    """

    execute(get_instances, ENVIRONMENT)
    execute(uninstall_latencyd)

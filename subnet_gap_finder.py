#!/usr/bin/env python3

# Python libs
import argparse
import ipaddress
import logging
import sys

# Flag to turn off AWS functionality (for lightweight use case)
REQUIRE_BOTO = True

# Third-party libs
try:
    if REQUIRE_BOTO:
        from botocore.exceptions import ClientError
        import boto3
    from tabulate import tabulate
    import netaddr
except ImportError as exc:
    print(f'{exc}')
    exit(1)

log = logging.getLogger(__name__)


def _convert_to_ips(str_nets):
    '''
    Convert a list of strings to a list of IP networks. Any garbage is thrown out.
    '''
    ip_nets = []

    for net in str_nets:
        try:
            ip_nets.append(ipaddress.ip_network(net))
        except ValueError:
            continue

    return sorted(ip_nets)


def find_ip_gaps(ip_nets):
    '''
    Given an input of a list of IP networks, compare the list to find gaps which can be used for new subnets.
    '''
    ret = []

    try:
        last_net = ip_nets[0]
    except IndexError:
        log.error(f'No IP networks found!')
        return

    for this_net in ip_nets:
        if last_net == this_net:
            continue

        if int(this_net.network_address) - int(last_net.broadcast_address) > 1:
            start_ip = last_net.broadcast_address + 1
            end_ip = this_net.network_address - 1
            log.info('Found gap from {0} to {1}'.format(start_ip, end_ip))
            gap = {'start': start_ip, 'end': end_ip, 'cidrs': []}

            for x in netaddr.cidr_merge(list(netaddr.iter_iprange(str(start_ip), str(end_ip)))):
                log.info(f'Base CIDR for gap: {x}')
                gap['cidrs'].append(x)

            ret.append(gap)

        last_net = this_net

    return ret


def file_gaps(filename):
    '''
    Find subnet gaps in a file containing a newline-spearated list of networks.
    '''
    try:
        with open(filename, 'r') as f:
            str_nets = f.read().split('\n')
    except FileNotFoundError as exc:
        log.error(f'{exc}')
        return

    return find_ip_gaps(_convert_to_ips(str_nets))


def vpc_gaps(vpc_id):
    '''
    Connect to AWS and find subnets associated with a VPC. Gaps between the subnets will be reported. If no gaps
    between subnets are found, We'll check for gaps between the last subnet and the end of the VPC space.
    '''
    if not REQUIRE_BOTO:
        log.error(f'AWS functionality is disabled!')
        return

    try:
        ec2_client = boto3.client('ec2')
        sn_return = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        sn_cidrs = _convert_to_ips([sn.get('CidrBlock') for sn in sn_return.get('Subnets', [])])
    except ClientError as exc:
        log.error(f'Unable to get subnet info: {exc}')
        return

    gaps = find_ip_gaps(sn_cidrs)

    if not gaps:
        try:
            vpc_return = ec2_client.describe_vpcs(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            vpc_cidr = _convert_to_ips([vpc.get('CidrBlock') for vpc in vpc_return.get('Vpcs', [])])[0]
        except ClientError as exc:
            log.error(f'Unable to get VPC info: {exc}')
            return

        if int(vpc_cidr.broadcast_address) - int(sn_cidrs[-1].broadcast_address) > 1:
            start_ip = sn_cidrs[-1].broadcast_address + 1
            end_ip = vpc_cidr.broadcast_address
            log.info('Found gap from {0} to END OF VPC {1}'.format(start_ip, end_ip))
            gap = {'start': start_ip, 'end': end_ip, 'cidrs': []}

            for x in netaddr.cidr_merge(list(netaddr.iter_iprange(str(start_ip), str(end_ip)))):
                log.info(f'Base CIDR for gap: {x}')
                gap['cidrs'].append(x)

            gaps.append(gap)

    return gaps


def _highlander(*args):
    '''
    Convenience function which ensures exactly one passed parameter has a value.
    '''
    return sum(bool(a) for a in args) == 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Utility script to show unused gaps in IP space within a list of networks.'
    )

    parser.add_argument('--filename', '-f', dest='filename', type=str,
                        help='Path to a file containing a list of IP networks. '
                             'EITHER "filename" OR "vpcid" IS REQUIRED')

    parser.add_argument('--loglevel', '-l', dest='loglevel', type=str, default='WARN',
                        help='Specify log level as text string: ERROR, WARNING, INFO, DEBUG')

    parser.add_argument('--vpcid', '-i', dest='vpc_id', type=str,
                        help='ID of a VPC in AWS to query. Subnets will be checked as the list of networks. '
                             'EITHER "filename" OR "vpcid" IS REQUIRED.')

    args = parser.parse_args()

    try:
        log.setLevel(args.loglevel.upper())
    except ValueError as exc:
        print(f'Failed to set log level ({exc}) Using default.')
        log.setLevel(parser.get_default('loglevel'))

    log_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)-5.5s]  %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)

    if not _highlander(args.filename, args.vpc_id):
        log.error('Either filename or VPC ID should be specified.')
        exit(1)

    if args.filename:
        gaps = file_gaps(args.filename)

    elif args.vpc_id:
        gaps = vpc_gaps(args.vpc_id)

    if not gaps:
        log.error('No information returned!')
        exit(1)

    print(
        tabulate(
            [[g['start'], g['end'], ', '.join([str(n) for n in g['cidrs']])] for g in gaps],
            headers=['Gap Start', 'Gap End', 'Gap CIDRs'],
            tablefmt='orgtbl'
        )
    )

    exit(0)

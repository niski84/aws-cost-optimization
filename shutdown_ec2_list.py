#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "Shutdown ec2 instanceid\'s supplied in text file"
#

import boto3
import json
import argparse
import time
import botocore
from datetime import datetime

## ----------------------------------------------------
## Configuration variables (defaults)
##
aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
shutdown_file_default = "./ec2_instances_to_shutdown.txt"
anti_hammer_sleep_interval = "0.5"
## ----------------------------------------------------

dryrun = True
aws_profile = ""
aws_region = ""
mode = ""
shutdownlist = ""


def main():

    # Ensure the user provided valid arguments
    validate_script_inputs()
    print "shutdown list : " +shutdownlist

    # Read in the istancesids to shutdown from text file
    instanceids_shutdown_list = import_shutdown_list(shutdownlist)

    # contect to aws
    #conenct_aws()

    # Shutdown the instances
    shutdown_instances(aws_profile,aws_region,dryrun,instanceids_shutdown_list)


def import_shutdown_list(file_location):
    try:
        f = open (file_location,'r')
        instanceids_shutdown_list = f.read().splitlines()
    except Exception as e:
        print "Error reading instanceids to shutdown from file {0}\n".format(file_location)
        print "Did you remember to specify a --shutdownlist argument?  Use the --help argument for more information."
        print "If the --shutdown argument is not provided, the default location is read from: {0}".format(shutdown_file_default)
        exit()

    return instanceids_shutdown_list


def shutdown_instances(aws_profile,aws_region,dryrun,instanceids_shutdown_list):
    global anti_hammer_sleep_interval
    boto3.setup_default_session(profile_name=aws_profile)
    ec2 = boto3.resource('ec2', region_name=aws_region)
    ec2_client = boto3.client('ec2',region_name=aws_region)

    # shut instances down if provided in shutdownlist
    for instanceid in instanceids_shutdown_list:
        shutdown_instance(instanceid, dryrun, mode, ec2, ec2_client)

    time.sleep(float(anti_hammer_sleep_interval))


def shutdown_instance(instanceid, dryrun, mode, ec2, ec2_client):
    global anti_hammer_sleep_interval

    if dryrun == False:
        print "{0} EC2 instance id: {1}".format(mode,instanceid)
        try:
            if mode == 'shutdown':
                ec2_client.create_tags(Resources=[instanceid], Tags=[{'Key':'STOPPED_NON_COMPLIANT_TAGGING', 'Value':'Stopped due to non-compliant tagging '+str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}])
                ec2_client.stop_instances(InstanceIds=[instanceid])

            if mode == 'MARK_FOR_DELETION':
                ec2_client.create_tags(Resources=[instanceid], Tags=[{'Key':'MARKED_FOR_DELETION', 'Value':''}])


        except Exception as e:
            print e
        time.sleep(0.5)
    else:
        if mode == 'shutdown':
            print "DryRun: Would have shudown instance: {0}".format(instanceid)
        if mode == 'MARK_FOR_DELETION':
            print "DryRun: Would have added MARKED_FOR_DELETION tag for isntance {0}".format(instanceid)

def validate_script_inputs():
    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--dryrun", help="Dry Run. defaults to True (dry run). \
        Note: dryrun=False must be supplied in order make changes to AWS", choices=['True', 'False'], default=True)
    parser.add_argument("--shutdownlist", help="list of instanceids to shutdown. (one instanceid per line).\
        If argument not specified, {0} will be used: ".format(shutdown_file_default), default=shutdown_file_default)
    parser.add_argument("--mode", help="2 modes are available: add a tag MARK_FOR_DELETION, or Shutdown the ec2 instance", \
        choices=['MARK_FOR_DELETION','shutdown'], default='MARK_FOR_DELETION')
    args = parser.parse_args()

    global aws_profile
    aws_profile = args.profile
    if aws_profile == "":
        aws_profile = aws_profile_default
        print "-profile argument not provided, defaulting to "+aws_profile_default

    global aws_region
    aws_region = args.region
    if aws_region == "":
        aws_region = aws_region_default
        print "-region argument not provided, defaulting to "+aws_region_default

    global dryrun
    if str(args.dryrun).lower() == "false":
        dryrun = False

    global mode
    if str(args.mode).lower() == "shutdown":
        mode = "shutdown"
    if str(args.mode).upper() == "MARK_FOR_DELETION":
        mode = "MARK_FOR_DELETION"

    global shutdownlist
    shutdownlist = args.shutdownlist
    if shutdownlist == "":
        shutdownlist = shutdownlist_default
        print "-shutdownlist argument not provided, defaulting to "+shutdownlist_default

if __name__ == "__main__":
    main()

#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "delete ebs volumes driven by csv file. optionally snapshot"
#

import boto3
import botocore
import json
import argparse
import csv
from collections import OrderedDict
from os.path import expanduser
import ConfigParser
import time
import numpy as np
## ----------------------------------------------------
## Configuration variables (defaults)
##

filter_on_role_name_default="/taggingaudit/predix-cap-taggingaudit-service"
aws_config_default='~/.aws/config'
## ----------------------------------------------------

aws_profile = ""
aws_region = ""
aws_config = ""
inputfile = ""
filter_on_rolename = ""
bool_dry_run=True

def main():

    # validate user inputs
    validate_script_inputs()

    # read in the inputfile
    spreedsheet = read_csv_to_dict(inputfile)

    # read in aws config file
    aws_config = get_filtered_aws_config_profiles(filter_on_role_name, aws_config_default)

    # connect to account; prompt mfa; do whatever
    process_spreedsheet(spreedsheet,aws_config)

# get profiles from ~/.aws/config filtered by certain role_arn's
def get_filtered_aws_config_profiles(filter_on_role_name, config_location):
    profiles_to_use = {}
    print 'config location: ',config_location
    profiles = botocore.configloader.load_config(config_location)['profiles']

    for profile,profile_config in profiles.items():
        if 'role_arn' in profile_config:
            parsed_role = profile_config['role_arn'].split('role')[1]
            if filter_on_role_name == parsed_role:
                profiles_to_use[profile] = profile_config

    return profiles_to_use



# process the spreedsheet, switch aws account when neccessary
def process_spreedsheet(spreedsheet,aws_config):

    # find profile with matching name of the profile on the current row
    current_profile = ""
    for row in spreedsheet:
        for profile, profile_data in aws_config.items():
            if row['Account ID'] in profile:
                 if not current_profile == profile:
                     ec2_client = connect_aws(profile,profile_data["region"])
                     current_profile = profile
                     break

        try:
            # create a snapshot if spreedsheet has yes value
            if row['Snapshot before delete?'].lower() == 'yes':
                response = ec2_client.create_snapshot(
                Description='Snapshot of {vol_id}'.format(vol_id=row['Volume ID']),
                VolumeId=row['Volume ID'],
                DryRun=dry_run
                )
                print 'Created {vol_size} GiB Snapshot. Snapshot ID: {snapshot_id}, Description: {desc}'.format(desc=response['Description'],vol_size=response['VolumeSize'],snapshot_id=response['SnapshotId'])


            # delete volume
            response = ec2_client.delete_volume(
                VolumeId=row['Volume ID'],
                DryRun=dry_run
            )
            print response
            print 'Deleted Volume: {volume_id} Request ID: {request_id}'.format(volume_id=row['Volume ID'],request_id=response['RequestId'])
        except Exception as e:
            print e


# connect to account with profile name in aws config
def connect_aws(profile_name,region_name):
    print "connecting to aws using the {0} profile".format(profile_name)
    profile_name = profile_name
    boto3.setup_default_session(profile_name=profile_name)

    ec2_client = boto3.client('ec2',region_name=region_name)

    print "logged into {0} region".format(region_name)
    print "using {0} account.".format(boto3.client('sts').get_caller_identity()['Account'])

    return ec2_client

# read csv into dict
def read_csv_to_dict(inputfile):
    with open(inputfile, 'rt') as f:
        csv_data = []
        reader = csv.DictReader(f)
        for row in reader:
            csv_data.append(row)

    return csv_data

def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--input", help="input filename")
    parser.add_argument("--filter_on_role_name", help="Role Name to filter aws config with")
    parser.add_argument("--aws_config", help="default location of aws config and credentials", default=aws_config_default)
    parser.add_argument("--dry_run", help="dry run?", default=False, action="store_true")

    args = parser.parse_args()

    global inputfile
    inputfile = args.input
    if inputfile == None:
        print "No --input argument supplied. You must include a csv file"
        exit(1)

    global filter_on_role_name
    filter_on_role_name = args.filter_on_role_name
    if filter_on_role_name == None:
        filter_on_role_name = filter_on_role_name_default
        print "--profile argument not provided, defaulting to "+filter_on_role_name_default

    global aws_config
    aws_config = args.aws_config

    global dry_run
    dry_run = args.dry_run


if __name__ == "__main__":
    main()

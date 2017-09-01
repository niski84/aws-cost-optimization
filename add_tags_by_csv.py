#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "AWS create tags, driven by csv file"
#

import boto3
import json
import argparse
import csv
from collections import OrderedDict
from os.path import expanduser
import ConfigParser
import time
## ----------------------------------------------------
## Configuration variables (defaults)
##

aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
## ----------------------------------------------------

aws_profile = ""
aws_region = ""
inputfile = ""


def main():

    # validate user inputs
    validate_script_inputs()

    # read in the inputfile
    spreedsheetrows = get_instance_list(inputfile)

    # read in aws config file
    aws_config = get_aws_config()

    # connect to account; prompt mfa; create/update tags
    update_tags(spreedsheetrows,aws_config)


# Read the ~/.aws_config into memory
def get_aws_config():
    home = expanduser("~")
    config = ConfigParser.ConfigParser()
    config.read(home + "/.aws/config")

    # convert into a dictionary so it's easier to work with
    aws_config = {}
    for section in config.sections():
        aws_config[section] = {}
        for option in config.options(section):
            aws_config[section][option] = config.get(section, option)

    return aws_config

# update aws tags driven by list and aws config
def update_tags(spreedsheetrows,aws_config):

    # find profile with matching name of the profile on the current row
    current_profile = ""
    for row in spreedsheetrows:
        for profile, profile_data in aws_config.items():
            if row["profile_name"].lower() in profile.lower():
                if not current_profile == profile:
                    ec2_client = connect_aws(profile,profile_data["region"])
                    current_profile = profile
                    break

        print "tagging with the following " + row["profile_name"], row["instance_id"],row["name_tag"],row["app_tag"],row["appowner_tag"],row["env_tag"]

        # try to create tag, sometime instace ids have been terminated and exception is thrown
        try:
            ec2_client.create_tags(Resources=[row["instance_id"]],
            Tags= [
            {'Key':'App', 'Value': row["app_tag"]}, \
            {'Key':'AppOwner', 'Value': row["appowner_tag"]}, \
            {'Key':'Environment', 'Value': row["env_tag"]} \
            ])
        except Exception as e:
            print e

        print "."
        # whoah, slow it down there cowboy
        time.sleep(.3)

def strip_key_name(value):
    if ":" in value:
        value_data = value.split(":")
        value = value_data[1].strip()
    return value

# connect to account with profile name in aws config
def connect_aws(profile_name,region_name):
    print "connecting to aws using the {0} profile".format(profile_name)
    profile_name = profile_name.replace("profile ","")
    boto3.setup_default_session(profile_name=profile_name)

    ec2_client = boto3.client('ec2',region_name=region_name)

    print "logged into {0} region".format(region_name)
    print "using {0} account.".format(boto3.client('sts').get_caller_identity()['Account'])

    return ec2_client

# read in the csv values into memory
def get_instance_list(inputfile):

    import csv
    reader = csv.reader(open(inputfile, 'r'))
    spreedsheetrows = []

    for row in reader:
       col = {}
       col["profile_name"], col["instance_id"],col["name_tag"],col["app_tag"],col["appowner_tag"],col["env_tag"] = row
       spreedsheetrows.append(col)
    return spreedsheetrows


def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--input", help="input filename")
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

    global inputfile
    inputfile = args.input
    if inputfile == None:
        print "No --input argument supplied. You must include a csv file"
        exit(1)



if __name__ == "__main__":
    main()

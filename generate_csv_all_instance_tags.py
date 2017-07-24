#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "Generate CSV report of all instance tags"
#
# Name => <datacenter>-<environment>-<org>-<customer>-<application>-<additional>
# Creator => Ex: CAP, PAAS, etc
# App => Ex: Cassandra, Redis, EMR, etc.
# AppOwner => (Acutal Customer who is using the app) Ex: Asset Team
# Contact => Ex: Asset team email address, dataservices email address, etc.
# CostCenter => Ex: GC48E2 (see attached xls from finance)
# Location => Ex: aws-us_west-2a (Cloud_provider-Region-AZ)
# Customer => Internal and External where applicable
# Environment => Prod, Dev, Staging, Sandbox, Perf, QA


import boto3
import json
import argparse
import csv

## ----------------------------------------------------
## Configuration variables (defaults)
##
aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
## ----------------------------------------------------

aws_profile = ""
aws_region = ""
outputfile = ""


def main():
    validate_script_inputs()
    ec2 = connect_aws()
    query_name_tags(ec2, outputfile)





def connect_aws():
    print "connecting to aws using the {0} profile".format(aws_profile)
    boto3.setup_default_session(profile_name=aws_profile)
    ec2 = boto3.resource('ec2', region_name=aws_region)
    my_session = boto3.session.Session()
    my_region = my_session.region_name
    print "logged into {0} region".format(my_region)
    print "using {0} account.".format(boto3.client('sts').get_caller_identity()['Account'])

    return ec2

def query_name_tags(ec2, outputfile):
    #report_file  = open(outputfile, "w")


    with open(outputfile, 'wb') as outfh:
        writer = csv.writer(outfh)

        header = ["instanceid", "start time","type", "private ip address", "level of compliance","Tags sorted alphabetically per instance -->"]
        writer.writerow(header)

        for instance in ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]):
            tags_message_leading_cols=[]
            tags_message=[]

            # The first few metadata items. t
            tags_message_leading_cols.append(instance.id)
            tags_message_leading_cols.append(str(instance.launch_time))
            tags_message_leading_cols.append(instance.instance_type)
            tags_message_leading_cols.append(str(instance.private_ip_address))

            if instance.tags is None:
                continue
            for tag in instance.tags:
                if tag['Key'] == 'NON_COMPLIANT_TAGGING':
                    tags_message_leading_cols.append(tag['Key'] + " : " + tag['Value'])
                else:
                    tags_message.append(tag['Key'] + " : " + tag['Value'])

            #try:
            if not any("NON_COMPLIANT_TAGGING" in s for s in tags_message_leading_cols):
                tags_message_leading_cols.append('OK')
            #except:
            #    print tags_message_leading_cols



            tags_message.sort()
            merged_tags = tags_message_leading_cols + tags_message
            #tags_message.append(instance.id + ", " + str(instance.launch_time) + ", " + instance.instance_type + ", " + tags_message)
            print merged_tags

            writer.writerow(merged_tags)

def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--output", help="Output filename", default="<profile>_tag_report.csv")
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

    global outputfile
    outputfile = args.output
    if outputfile == "<profile>_tag_report.csv":
        outputfile = aws_profile + "_tag_report.csv"



if __name__ == "__main__":
    main()

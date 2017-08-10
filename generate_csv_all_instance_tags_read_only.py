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
from collections import OrderedDict


## ----------------------------------------------------
## Configuration variables (defaults)
##

# holds required tags and the values found. OfderedDict to keep the columns lined up
required_fields = OrderedDict([('Name',''),('App',''),('AppOwner',''), ('Environment',''), ('Director','')])

aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
## ----------------------------------------------------

aws_profile = ""
aws_region = ""
outputfile = ""
filter_by_tag = ""



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

    with open(outputfile, 'wb') as outfh:
        writer = csv.writer(outfh)

        # header
        header = ["Account", "Region", "Availability Zone","Instance ID", "Instance State", "Launch Time","Instance Type","Private IP Address","Tenancy","Security Group"]

        # append required fields to header of report
        for key, value in required_fields.items():
            header.append(key + " tag")

        # write the header to report
        writer.writerow(header)

        print "Generating report ... "

        # if filter_by_tag argument was given, search on that.
        if filter_by_tag:
            instances = ec2.instances.filter(Filters=[{'Name': 'tag:' + filter_by_tag,'Values': ['*']}])
        else:
            # no filter_by_tag argument was given, so default to reporting on running instances
            instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

        # iterate thru all the instances returned by filter
        for instance in instances:

            # clear values from last run
            for key, value in required_fields.iteritems():
                required_fields[key] = ""

            # init
            tags_message_leading_cols=[]
            tags_message=[]

            # report outputs the account name as the name used in the /.aws/config file.
            # predix-management is the default account, so change the name so it doesn't
            # appear confusing on the report
            account_name = aws_profile
            if account_name == "default": account_name = "768198107322-Predix-Mgt"


            sec_group_text = ""
            for sec_groups in instance.security_groups:
                sec_group_text = sec_group_text + sec_groups['GroupName'] + ":" + sec_groups['GroupId'] + ","
            sec_group_text = sec_group_text.rstrip(",")

            # The first few metadata items.
            tags_message_leading_cols.append(account_name)
            tags_message_leading_cols.append(aws_region)
            tags_message_leading_cols.append(instance.placement['AvailabilityZone'])
            tags_message_leading_cols.append(instance.id)
            tags_message_leading_cols.append(instance.state['Name'])
            tags_message_leading_cols.append(str(instance.launch_time))
            tags_message_leading_cols.append(instance.instance_type)
            tags_message_leading_cols.append(str(instance.private_ip_address))
            tags_message_leading_cols.append(instance.instance_lifecycle)
            tags_message_leading_cols.append(sec_group_text)


            # some instances don't have ANY tags and will throw exception
            if instance.tags is None:
                pass
            else:
                # iterate through each tag to see if it's a required_field
                for tag in instance.tags:
                    for key, value in required_fields.iteritems():
                        if tag['Key'].lower() == key.lower():
                            required_fields[key] = "{0} : {1} ".format(tag['Key'], tag['Value'])

            # combine leading columns with required tags found
            merged_tags = tags_message_leading_cols + required_fields.values()

            # print merged_tags to report
            writer.writerow(merged_tags)

        print "Report output to: " + outputfile

def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--filter_by_tag", help="filter by tag name")
    parser.add_argument("--output", help="Output filename", default="<profile>_tag_report.csv")
    args = parser.parse_args()

    global aws_profile
    aws_profile = args.profile
    if aws_profile == "":
        aws_profile = aws_profile_default
        print "-profile argument not provided, defaulting to "+aws_profile_default

    global filter_by_tag
    filter_by_tag = args.filter_by_tag


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

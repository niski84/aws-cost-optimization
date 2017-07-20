#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "Evaluation of AWS EC2 instances for tag compliance.  If dryrun false, will add non_compliant_tag key tag with value \
      of missing required tags. WIP."
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
import time

## ----------------------------------------------------
## Configuration variables (defaults)
##
required_fields = ["Name", "App", "AppOwner", "Environment"]
non_compliant_tag_name = "NON_COMPLIANT_TAGGING"
aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
## ----------------------------------------------------

dryrun = True
aws_profile = ""
aws_region = ""



def main():
    validate_script_inputs()
    evaluate_compliance(aws_profile,aws_region,dryrun)

def evaluate_compliance(aws_profile,aws_region,dryrun):
    boto3.setup_default_session(profile_name=aws_profile)
    ec2 = boto3.resource('ec2', region_name=aws_region)
    ec2_client = boto3.client('ec2',region_name=aws_region)

    my_session = boto3.session.Session()

    print("region chosen:  {0}".format(aws_region))
    print("account: " + boto3.client('sts').get_caller_identity()['Account'])

    no_tags_count = 0


    untagged_instances = []
    # iterate over ALL EC2 instances
    for instance in ec2.instances.all():

        # keep track of which tags were found.
        # reset all required fields found to False
        required_fields_found = {}
        for required_field in required_fields:
            required_fields_found[required_field] = False
        non_compliant_message = ""
        non_compliant_tag_name_exists = False
        non_compliant_tag_name_value = ""

        # Some instances don't have any tags..
        tags = {}
        if instance.tags is None:
            untagged_instances.append(instance.id)
            if dryrun == False:
                # if there are no tags present, write the non_compliant_tag_name tag
                ec2.create_tags(Resources=[instance.id], Tags=[{'Key':non_compliant_tag_name, 'Value':'missing ALL required tags'},])
            no_tags_count += 1
            print "tagged as out of compliance: " + instance.id
            continue

        # Determine if required_tags are found
        tags = instance.tags
        for tag in instance.tags:
            for req_key, req_value in required_fields_found.items():
                if tag['Key'].lower() == req_key.lower():
                    required_fields_found[req_key] = True

            # Check if non_compliant_tag already exists
            if tag['Key'] == non_compliant_tag_name:
                non_compliant_tag_name_exists = True
                non_compliant_tag_name_value = tag['Value']


        # build non_compliant_message tag value
        print "checking instance:{0} for tag compliance...".format(instance.id)
        non_compliant = False
        non_compliant_message = "Missing "
        for key, value in required_fields_found.items():
            if value == False:
                non_compliant = True
                non_compliant_message = non_compliant_message + key + ", "
        non_compliant_message = non_compliant_message + "tag(s)"

        # if required tags are missing, create non_compliant_tagging tag
        if non_compliant == True:
            if dryrun == False:
                try:
                    # only write the tag if it doesn't already exist
                    if not non_compliant_message == non_compliant_tag_name_value:
                        print "Created tag for instance: " + instance.id + " key " + non_compliant_tag_name + " value: " + non_compliant_message
                        ec2.create_tags(Resources=[instance.id], Tags=[{'Key':non_compliant_tag_name, 'Value':non_compliant_message}])
                        time.sleep(0.3)
                except Exception as e:
                    print e
            else:
                print "DryRun: Would have created tag for instance: " + instance.id + " key " + non_compliant_tag_name + " value: " + non_compliant_message


        # If non_compliant_tag exists, but is now in compliance: remove non_compliant_tag
        if non_compliant == False and non_compliant_tag_name_exists == True:
            if dryrun == False:
                print instance.id + " has all required tags. Removing " + non_compliant_tag_name
                try:
                    ec2_client.delete_tags(Resources=[instance.id], Tags=[{"Key": non_compliant_tag_name}])
                except Exception as e:
                    print e
                time.sleep(1)
            else:
                print "DryRun: Would have removed " + non_compliant_tag_name + " tag for instance: " + instance.id


def validate_script_inputs():
    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--dryrun", help="Dry Run. defaults to True (dry run)", choices=['true', 'false'], default=True)
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


if __name__ == "__main__":
    main()

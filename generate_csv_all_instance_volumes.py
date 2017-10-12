#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "Generate CSV report of all instances volumes"
#


import boto3
import json
import argparse
import csv
import botocore.session
from collections import OrderedDict
import math
import os, sys
from datetime import datetime, timedelta



## ----------------------------------------------------
## Configuration variables (defaults)
##

role_name_default="/tf/predix-cap-taggingaudit"
bucket = 'predix-tagging-compliance'
key = 'csv_reports'

ebs_gb_month_cost = {"standard":".05","gp2":".10","io1":".125","io1_p_iops":".065","st1":".045","sc1":".025","snapshot":".05",}


## ----------------------------------------------------

# overcome issues with crontabs not knowing where their home is!
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


# dir where reports are written out to
report_dir = "./reports/ebs/"+str(datetime.now().strftime('%Y-%m-%d-%H-%s')+"/")

try:
    os.makedirs(report_dir)
except:
    pass


def calc_monthly_cost(GiBs,storage_type):
    total = float(GiBs) * float(ebs_gb_month_cost[storage_type])
    return '${:,.2f}'.format(total)



def main():

    # validate arguments provided on command line
    validate_script_inputs()

    # filter ~/.aws/config to fetch only profiles with the role we want to assume (ex: '/tf/predix-cap-taggingaudit' )
    profiles = get_filtered_aws_config_profiles(filter_on_role_name = role_name, config_location='~/.aws/config')

    if len(profiles) == 0:
        print "\nExiting. No profiles were found with the role name:", role_name, "in the ~/.aws/config file"
        print "use the --role_name argument to specify a valid role name contained in the ~/.aws/config file"
        exit()

    # connect to each resource, then run report for each profile
    # note: boto will prompt for mfa if it's needed
    for profile, profile_config in sorted(profiles.items()):
        print profile
        print profile,profile_config['region']
        ec2,ec2_client = connect_aws(profile,profile_config['region'])


        outputfile = report_dir + profile + "_ebs_report.csv"
        run_report(ec2,ec2_client,profile,profile_config['region'],outputfile)


    # combine the reports into one csv file
    combined_reports_file = concatonate_reports(report_dir)

    # upload the csv file to s3
    #upload_to_s3(combined_reports_file,bucket,key)


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

# connect to the various resource APIs. All in one function so if there's an access denied we know right away
# rather than halfway thru the report.
def connect_aws(aws_profile,aws_region):

    print "connecting to aws using the {0} profile in {1} region".format(aws_profile,aws_region)
    boto3.setup_default_session(profile_name=aws_profile)

    ec2 = boto3.resource('ec2',region_name=aws_region)
    ec2_client = boto3.client('ec2', region_name=aws_region)



    print "logged into {0} region".format(aws_region)
    print "using {0} account to assume roles.".format(boto3.client('sts').get_caller_identity()['Account'])

    return ec2, ec2_client



# main function to gather instance attributes and cloudwatch metrics
def run_report(ec2,ec2_client,aws_profile,aws_region, outputfile):

    try:
        os.makedirs(os.path.dirname(outputfile))
    except:
        pass



    with open(outputfile, 'wb') as outfh:
        writer = csv.writer(outfh)

        # report outputs the account name as the name used in the /.aws/config file.
        # predix-management is the default account, so change the name so it doesn't
        # appear confusing on the report
        if aws_profile == "default":
            account_id = "768198107322"
            account_name = "Predix-Mgt"
        else:
            account_id = aws_profile[:12]
            account_name = aws_profile[13:]


        # header
        header = ["Account ID","Account Name", "Region", "Availability Zone","Report Date", "Volume ID", "Volume State", "Volume Type","Create Time", \
        "Size (GiBs)","Cost Per Month","From Sanapshot ID"]

        # write the header to report
        writer.writerow(header)

        print "Generating report ... "


        vols = ec2_client.describe_volumes()
        for volume in vols['Volumes']:
            volume_report = []
            volume_report.append(account_id+'\t')
            volume_report.append(account_name)
            volume_report.append(aws_region)
            volume_report.append(volume['AvailabilityZone'])
            volume_report.append(datetime.now().strftime("%Y-%m-%d"))
            volume_report.append(volume['VolumeId'])
            volume_report.append(volume['State'])
            volume_report.append(volume['VolumeType'])
            volume_report.append(volume['CreateTime'].strftime('%Y-%m-%d'))
            volume_report.append(volume['Size'])

            # calc monthly cost
            cost_per_month = ''
            cost_per_month = calc_monthly_cost(volume['Size'],volume['VolumeType'])

            volume_report.append(cost_per_month)
            volume_report.append(volume['SnapshotId'])

            print volume_report



            # print merged_tags to report
            writer.writerow(volume_report)

        print "Report output to: " + outputfile


# upload report to s3 bucket and overwrite latest
def upload_to_s3(file_path,bucket,key):
    print "uploading to s3"
    boto3.setup_default_session(profile_name='default')
    s3 = boto3.client('s3')
    transfer = boto3.s3.transfer.S3Transfer(s3)
    file = os.path.basename(file_path)
    transfer.upload_file(file_path, bucket, key+"/"+file)
    transfer.upload_file(file_path, bucket, key+"/latest/"+"latest"+"_combined_accounts_ebs_report.csv")
    print "uploaded",file_path, bucket, key+"/"+file



# validate the script inputs and set defaults
def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)

    parser.add_argument("--role_name", help="Role Name to filter aws config with")
    parser.add_argument("--filter_by_tag", help="filter by tag name")


    args = parser.parse_args()

    global role_name
    role_name = args.role_name
    if role_name == None:
        role_name = role_name_default
        print "-profile argument not provided, defaulting to "+role_name_default

    global filter_by_tag
    filter_by_tag = args.filter_by_tag


# concatonate all the csv reports
def concatonate_reports(report_dir):
    filenames = []
    output_file = report_dir + str(datetime.now().strftime('%Y-%m-%d'))+"_combined_accounts_ebs_volumes_report.csv"

    # walk report dir to get report filenames
    files = [ f for f in os.listdir(report_dir) if os.path.isfile(os.path.join(report_dir,f)) ]
    for f in files:
        if "combined_accounts" not in f: #  avoid recursive read error
            filenames.append(f)

    # grab header
    with open(os.path.join(report_dir,filenames[0])) as infile:
        header = infile.readline()

    # open each file and combine them.
    # remove header on each report.
    with open(output_file, 'w') as outfile:
        outfile.write(header)
        for fname in filenames:
            with open(os.path.join(report_dir,fname)) as infile:
                infile.next() # skip header line
                for line in infile:
                    outfile.write(line)

    return output_file

if __name__ == "__main__":
    main()

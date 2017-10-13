
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
import socket
import struct

## ----------------------------------------------------
## Configuration variables (defaults)
##

role_name_default="/tf/predix-cap-taggingaudit"
bucket = 'predix-tagging-compliance'
key = 'csv_reports'




## ----------------------------------------------------

# overcome issues with crontabs not knowing where their home is!
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


# dir where reports are written out to
report_dir = "./reports/vpc/"+str(datetime.now().strftime('%Y-%m-%d-%H-%s')+"/")

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


        outputfile = report_dir + profile + "_subnets_report.csv"
        run_report(ec2,ec2_client,profile,profile_config['region'],outputfile)


    # combine the reports into one csv file
    combined_reports_file = concatonate_reports(report_dir)

    # upload the csv file to s3
    upload_to_s3(combined_reports_file,bucket,key)


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
def run_report(ec2,ec2_client,aws_profile,aws_region,outputfile):

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
        header = ['Account ID','Account Name','Region','Availability Zone','VPC ID','CIDR Block','Subnet Name','Subnet ID']

        # write the header to report
        writer.writerow(header)

        print "Generating report ... "

        subnets = ec2_client.describe_subnets()
        for subnet in subnets['Subnets']:
            subnets_report = []
            subnets_report.append(account_id+'\t')
            subnets_report.append(account_name)
            subnets_report.append(aws_region)
            subnets_report.append(subnet['AvailabilityZone'])
            subnets_report.append(subnet['VpcId'])
            subnets_report.append(subnet['CidrBlock'])
            # Cidr = subnet['CidrBlock'].split('/')[1]
            # print cidr_to_netmask(subnet['CidrBlock'])
            # print subnet['CidrBlock']
            #subnets_report.append(cidr_to_netmask(subnet['CidrBlock']))


            if 'Tags'in subnet:
                for tag in subnet['Tags']:
                    for key, value in tag.iteritems():
                        if value == 'Name':
                            subnets_report.append(tag['Value'])
                            print tag['Value']

            else:
                subnets_report.append('')
            subnets_report.append(subnet['SubnetId'])



        # print merged_tags to report
        writer.writerow(subnets_report)

        print "Report output to: " + outputfile

def cidr_to_netmask(cidr):
    network, net_bits = cidr.split('/')
    host_bits = 32 - int(net_bits)
    netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
    return network, netmask

# upload report to s3 bucket and overwrite latest
def upload_to_s3(file_path,bucket,key):
    print "uploading to s3"
    boto3.setup_default_session(profile_name='default')
    s3 = boto3.client('s3')
    transfer = boto3.s3.transfer.S3Transfer(s3)
    file = os.path.basename(file_path)
    transfer.upload_file(file_path, bucket, key+"/"+file)
    transfer.upload_file(file_path, bucket, key+"/latest/"+"latest"+"_combined_accounts_subnets_report.csv")
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
        print "--profile argument not provided, defaulting to "+role_name_default

    global filter_by_tag
    filter_by_tag = args.filter_by_tag


# concatonate all the csv reports
def concatonate_reports(report_dir):
    filenames = []
    output_file = report_dir + str(datetime.now().strftime('%Y-%m-%d'))+"_combined_accounts_subnets_report.csv"

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

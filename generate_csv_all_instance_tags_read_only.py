#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "Generate CSV report of all instances on instance attributes and cloudwatch metrics"
#
# Name => <datacenter>-<environment>-<org>-<customer>-<application>-<additional>
# App => Ex: Cassandra, Redis, EMR, etc.
# AppOwner => (Acutal Customer who is using the app) Ex: Asset Team
# Environment => Prod, Dev, Staging, Sandbox, Perf, QA


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

# holds required tags and the values found. OfderedDict to keep the columns lined up
required_fields = OrderedDict([('Name',''),('App',''),('AppOwner',''), ('Environment',''), ('Director','')])

role_name_default="/tf/predix-cap-taggingaudit"
bucket = 'predix-tagging-compliance'
key = 'csv_reports'
cloudwatch_time_delta = timedelta(days=14) # request to set to 14 days even though it's run daily..
aws_config_default='./.aws/config'
## ----------------------------------------------------

role_name = ""
outputfile = ""
filter_by_tag = ""
use_cloudwatch = ""
cw = ""

# overcome issues with crontabs not knowing where their home is!
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


# dir where reports are written out to
report_dir = "./reports/"+str(datetime.now().strftime('%Y-%m-%d-%H-%s')+"/")

try:
    os.makedirs(report_dir)
except:
    pass

def main():

    # validate arguments provided on command line
    validate_script_inputs()

    print "time delta is {0}".format(cloudwatch_time_delta)
    print "the output directory for reports is: {0}".format(report_dir)

    # filter ~/.aws/config to fetch only profiles with the role we want to assume (ex: '/tf/predix-cap-taggingaudit' )
    profiles = get_filtered_aws_config_profiles(filter_on_role_name = role_name, config_location = aws_config)

    if len(profiles) == 0:
        print "\nExiting. No profiles were found with the role name:", role_name, "in the ~/.aws/config file"
        print "use the --role_name argument to specify a valid role name contained in the ~/.aws/config file"
        exit()

    # connect to each resource, then run report for each profile
    # note: boto will prompt for mfa if it's needed
    for profile, profile_config in profiles.items():
        print profile
        ec2,ec2_client,cw,asg = connect_aws(profile,profile_config['region'],aws_config)
        outputfile = report_dir + profile + "_tag_report.csv"
        run_report(ec2,cw,asg,profile,profile_config['region'],cloudwatch_time_delta,use_cloudwatch,outputfile)


    # combine the reports into one csv file
    combined_reports_file = concatonate_reports(report_dir)

    # upload the csv file to s3
    upload_to_s3(combined_reports_file,bucket,key)


# get profiles from ~/.aws/config filtered by certain role_arn's
def get_filtered_aws_config_profiles(filter_on_role_name, config_location):
    profiles_to_use = {}

    profiles = botocore.configloader.raw_config_parse(config_location)

    for profile,profile_config in profiles.items():
        if 'role_arn' in profile_config:
            parsed_role = profile_config['role_arn'].split('role')[1]

            if filter_on_role_name == parsed_role:
                profiles_to_use[profile.replace('profile ','')] = profile_config

    return profiles_to_use

# connect to the various resource APIs. All in one function so if there's an access denied we know right away
# rather than halfway thru the report.
def connect_aws(aws_profile,aws_region,aws_config):
    print "connecting to aws using the {0} profile in {1} region".format(aws_profile,aws_region)

    print "using aws config file:",aws_config
    os.environ["AWS_CONFIG_FILE"] = aws_config

    boto3.setup_default_session(profile_name=aws_profile)

    ec2 = boto3.resource('ec2',region_name=aws_region)
    ec2_client = boto3.client('ec2', region_name=aws_region)
    asg = boto3.client('autoscaling', region_name=aws_region)

    if use_cloudwatch == "true":
        cw = boto3.client('cloudwatch', region_name=aws_region)
    else:
        cw = ""


    print "logged into {0} region".format(aws_region)
    print "using {0} account to assume roles.".format(boto3.client('sts').get_caller_identity()['Account'])

    return ec2, ec2_client,cw,asg


# main function to gather instance attributes and cloudwatch metrics
def run_report(ec2,cw,asg,aws_profile,aws_region,cloudwatch_time_delta, use_cloudwatch, outputfile):

    try:
        os.makedirs(os.path.dirname(outputfile))
    except:
        pass

    with open(outputfile, 'wb') as outfh:
        writer = csv.writer(outfh)

        # header
        header = ["Account ID","Account Name", "Region", "Availability Zone","Report Date", "Instance ID", "Instance State", "Launch Time", \
        "Instance Type","Private IP Address","Tenancy","Security Group","AMI-ID","Memory","Pricing Type","Auto Scaling Group Name"]

        # cloudwatch headers (seperated so it can be turned on and off easily)
        cloudwatch_headers=["Average CPU Utilization", \
        "Maximum CPU Utilization","Disk Read (Bytes)","Disk Write (Bytes)","Network In (Bytes)","Network Out (Bytes)"]
        header = header + cloudwatch_headers

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
            # no filter_by_tag argument was given, so default to reporting on all instances
            instances = ec2.instances.all()


        # report outputs the account name as the name used in the /.aws/config file.
        # predix-management is the default account, so change the name so it doesn't
        # appear confusing on the report
        if aws_profile == "default":
            account_id = "768198107322"
            account_name = "Predix-Mgt"
        else:
            account_id = aws_profile[:12]
            account_name = aws_profile[13:]

        size = sum(1 for _ in instances)

        print "Search returned {0} instances".format(size)
        # iterate thru all the instances returned by filter
        for instance in instances:
            print "on instance {0} ".format(instance)
            # clear values from last run
            for key, value in required_fields.iteritems():
                required_fields[key] = ""

            # init
            tags_message_leading_cols=[]
            tags_message=[]

            sec_group_text = ""
            for sec_groups in instance.security_groups:
                sec_group_text = sec_group_text + sec_groups['GroupName'] + ":" + sec_groups['GroupId'] + ","
            sec_group_text = sec_group_text.rstrip(",")

            # The first few metadata items.
            tags_message_leading_cols.append(account_id)
            tags_message_leading_cols.append(account_name)
            tags_message_leading_cols.append(aws_region)
            tags_message_leading_cols.append(instance.placement['AvailabilityZone'])
            tags_message_leading_cols.append(datetime.now().strftime("%Y-%m-%d"))
            tags_message_leading_cols.append(instance.id)
            tags_message_leading_cols.append(instance.state['Name'])
            tags_message_leading_cols.append(str(instance.launch_time))
            tags_message_leading_cols.append(instance.instance_type)
            tags_message_leading_cols.append(str(instance.private_ip_address))
            tags_message_leading_cols.append(instance.instance_lifecycle)
            tags_message_leading_cols.append(sec_group_text)
            tags_message_leading_cols.append(instance.image_id) # AMI-ID
            tags_message_leading_cols.append("") # Memory (requires amazon python scripts to collect metrics)
            tags_message_leading_cols.append("") # Pricing Type - only available thru aws billing
            tags_message_leading_cols.append(get_autoscale_group(asg, instance.id)) # Autoscaling Group

            # if use_cloudwatch comamnd line paramater wasn't set to false, then retrieve the (time consuming) cloudwatch metrics
            if use_cloudwatch == "true":
                tags_message_leading_cols.append(get_cloudwatch_metric('cpu_avg',instance.id,cloudwatch_time_delta,aws_region,cw))
                tags_message_leading_cols.append(get_cloudwatch_metric('cpu_max',instance.id,cloudwatch_time_delta,aws_region,cw))
                tags_message_leading_cols.append(get_cloudwatch_metric('disk_read_bytes',instance.id,cloudwatch_time_delta,aws_region,cw))
                tags_message_leading_cols.append(get_cloudwatch_metric('disk_write_bytes',instance.id,cloudwatch_time_delta,aws_region,cw))
                tags_message_leading_cols.append(get_cloudwatch_metric('network_in_bytes',instance.id,cloudwatch_time_delta ,aws_region,cw))
                tags_message_leading_cols.append(get_cloudwatch_metric('network_out_bytes',instance.id,cloudwatch_time_delta,aws_region,cw))
            else:
                tags_message_leading_cols.append("")
                tags_message_leading_cols.append("")
                tags_message_leading_cols.append("")
                tags_message_leading_cols.append("")
                tags_message_leading_cols.append("")
                tags_message_leading_cols.append("")

            # some instances don't have ANY tags and will throw exception
            if instance.tags:
                # iterate through each tag to see if it's a required_field
                for tag in instance.tags:
                    for key, value in required_fields.iteritems():
                        if tag['Key'].lower() == key.lower():
                            required_fields[key] = "{1}".format(tag['Key'], tag['Value'])

            # combine leading columns with required tags found
            merged_tags = tags_message_leading_cols + required_fields.values()

            # print merged_tags to report
            writer.writerow(merged_tags)

        print "Report output to: " + outputfile

# get the Autoscaling group instance id is a member of, else return None
def get_autoscale_group(asg, instance_id):
    try:
        instances = asg.describe_auto_scaling_instances(InstanceIds=[instance_id])
        get_autoscale_group = instances['AutoScalingInstances']
    except Exception as e:
        print e

    if get_autoscale_group:
        return get_autoscale_group[0]['AutoScalingGroupName']
    return None

# upload report to s3 bucket and overwrite latest
def upload_to_s3(file_path,bucket,key):
    print "uploading to s3"
    boto3.setup_default_session(profile_name='default')
    s3 = boto3.client('s3')
    transfer = boto3.s3.transfer.S3Transfer(s3)
    file = os.path.basename(file_path)
    transfer.upload_file(file_path, bucket, key+"/"+file)
    transfer.upload_file(file_path, bucket, key+"/latest/"+"latest"+"_combined_accounts_tagging_report.csv")
    print "uploaded",file_path, bucket, key+"/"+file

# get cloud watch metrics.
# valid metric params are : cpu_avg , cpu_max , disk_read_bytes , disk_write_bytes , network_in_bytes , network_out_bytes
def get_cloudwatch_metric(metric_query,instanceid,time_delta,aws_region,cw):

    dim = [{'Name': 'InstanceId', 'Value': instanceid}]
    period = 3600 # 3600 == 1 hr
    endTime = datetime.now()
    startTime = endTime - time_delta

    if metric_query.lower() == "cpu_avg":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistics=['Average'],
        Dimensions=dim)

        if metric['Datapoints']:
             data = metric['Datapoints'][0]['Average']
             return "{0}%".format(data)

    if metric_query.lower() == "cpu_max":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistics=['Maximum'],
        Dimensions=dim)

        if metric['Datapoints']:
            data = metric['Datapoints'][0]['Maximum']
            return "{0}%".format(data)

    if metric_query.lower() == "disk_read_bytes":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='DiskReadBytes',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=dim)

        if metric['Datapoints']:
            data = metric['Datapoints'][0]['Sum']
            return data

    if metric_query.lower() == "disk_write_bytes":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='DiskWriteBytes',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=dim)

        if metric['Datapoints']:
            data = metric['Datapoints'][0]['Sum']
            return data

    if metric_query.lower() == "network_in_bytes":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='NetworkIn',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=dim)

        if metric['Datapoints']:
            data = metric['Datapoints'][0]['Sum']
            return data

    if metric_query.lower() == "network_out_bytes":
        metric = cw.get_metric_statistics(Period=period,
        StartTime=startTime,
        EndTime=endTime,
        MetricName='NetworkOut',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=dim)

        if metric['Datapoints']:
            data = metric['Datapoints'][0]['Sum']
            return data

# cloudwatch returns values in Bytes; yuck.  Convert to human readable data sizes
# not using, was asked to return bytes instead
def get_human_readable_filesize(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

# validate the script inputs and set defaults
def validate_script_inputs():

    parser = argparse.ArgumentParser(description=prog_desc)

    parser.add_argument("--role_name", help="Role Name to filter aws config with")
    parser.add_argument("--filter_by_tag", help="filter by tag name")
    parser.add_argument("--aws_config", help="default location of aws config and credentials", default=aws_config_default)
    parser.add_argument("--use_cloudwatch", help="Add Cloudwatch Metrics", default="true")



    args = parser.parse_args()

    global role_name
    role_name = args.role_name
    if role_name == None:
        role_name = role_name_default
        print "-profile argument not provided, defaulting to "+role_name_default

    global filter_by_tag
    filter_by_tag = args.filter_by_tag

    global use_cloudwatch
    use_cloudwatch = args.use_cloudwatch

    global aws_config
    aws_config = args.aws_config


# concatonate all the csv reports
def concatonate_reports(report_dir):
    filenames = []
    output_file = report_dir + str(datetime.now().strftime('%Y-%m-%d'))+"_combined_accounts_tagging_report.csv"

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

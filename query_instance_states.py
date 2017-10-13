#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "query ec2 instanceid\'s state (stopped, running, etc) supplied in text file"
#

import boto3
import json
import argparse
import time
import botocore
from datetime import datetime
import csv

## ----------------------------------------------------
## Configuration variables (defaults)
##
aws_profile_default = "predix-w2-cf3"
aws_region_default = "us-west-2"
querylist_default = "./ec2_instances_to_query.txt"
outputfile_default = "./"
anti_hammer_sleep_interval = "0.5"
## ----------------------------------------------------


aws_profile = ""
aws_region = ""
instanceids_list = ""


def main():

    # Ensure the user provided valid arguments
    validate_script_inputs()
    #test()

    #exit()

    # Read in the istancesids to shutdown from text file
    instanceids_list = import_query_list(querylist)

    boto3.setup_default_session(profile_name=aws_profile)
    ec2 = boto3.resource('ec2', region_name=aws_region)
    ec2_client = boto3.client('ec2',region_name=aws_region)


    while True:
        query_instances_state(aws_profile,aws_region,instanceids_list,ec2,ec2_client)
        time.sleep(600)




def import_query_list(file_location):
    try:
        f = open (file_location,'r')
        instanceids_list = f.read().splitlines()
    except Exception as e:
        print "Error reading instanceids to shutdown from file {0}\n".format(file_location)
        print "Did you remember to specify a --querylist argument?  Use the --help argument for more information."
        print "If the --querylist argument is not provided, the default location is read from: {0}".format(querylist_default)
        exit()

    return instanceids_list


def query_instances_state(aws_profile,aws_region,instanceids_query_list,ec2,ec2_client ):
    global anti_hammer_sleep_interval

    stopped_count = 0
    running_count = 0
    stopped_instance_ids = []


    instances = ec2.instances.all()

    for instance in instances:
        if instance.id in instanceids_query_list:

            if instance.state["Name"] == 'running':
                running_count = running_count + 1
            else:
                stopped_count = stopped_count + 1

                # write all this out to a file to compute cost later
                stopped_instance_ids.append(instance.id)

    write_stopped_state_instanceids_to_file(stopped_instance_ids,get_outputfile_default())

    print str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print "stopped instance: " + str(stopped_count)
    print "running instances: " + str(running_count)
    print "\n"


    #output_still_stopped(get_outputfile_default(), outputs)

def write_stopped_state_instanceids_to_file(stopped_instance_ids,outputfile):
    outfile = open(outputfile, 'w')

    for item in stopped_instance_ids:
        outfile.write("%s\n" % item)

def output_still_stopped(outputfile, outputs):

    # defunct function

    with open(outputfile, 'wb') as outfh:
        writer = csv.writer(outfh)

        line = ""
        for output in outputs:
            print output
            line = []
            for key, value in output.iteritems():
                line.append(value)
                #print "this is the line " + line
            print "final line is " + str(line)
            writer.writerow(line)


def validate_script_inputs():
    parser = argparse.ArgumentParser(description=prog_desc)
    parser.add_argument("--profile", help="AWS profile: "+aws_profile_default, default=aws_profile_default)
    parser.add_argument("--region", help="AWS region: "+aws_region_default, default=aws_region_default)
    parser.add_argument("--querylist", help="list of instanceids to query state. (one instanceid per line).\
        If argument not specified, {0} will be used: ".format(querylist_default), default=querylist_default)
    parser.add_argument("--outputfile", help="file to output stopped instance data for savings: "+outputfile_default, default=outputfile_default)

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



    global querylist
    querylist = args.querylist
    if querylist == "":
        querylist = querylist_default
        print "-querylist argument not provided, defaulting to "+querylist_default

    global outputfile
    outputfile = args.outputfile
    if outputfile == "":
        outputfile = get_outputfile_default()
        print "-outputfile argument not provided, defaulting to "+outputfile

def get_outputfile_default():
    outputfile = aws_profile + "_for_savings_report.csv"
    return outputfile


if __name__ == "__main__":
    main()

import argparse
import boto3
import datetime
from dateutil.tz import tzutc


def is_in_autoscale_group(region, instance_id):
    asg = boto3.client('autoscaling', region_name=region)
    instances = \
        asg.describe_auto_scaling_instances(InstanceIds=[instance_id])
    instance_status = instances['AutoScalingInstances']
    if instance_status:
        print "Instance %s is in autoscale group %s" \
              % (instance_id, instance_status[0]['AutoScalingGroupName'])
        return True
    return False


def find_idle_instances(region, tag_key, tag_values,
                        idle_period_secs, minimum,outputfile):
    ec2 = boto3.client('ec2', region_name=region)
    ec2res = boto3.resource('ec2', region_name=region)
    c = boto3.client('cloudwatch', region_name=region)
    values = tag_values.split(",")
    filters = []
    if tag_key:
        f0 = {}
        f0['Name'] = "tag:{}".format(tag_key)
        f0['Values'] = values
        filters.append(f0)

    f1 = {}
    f1['Name'] = 'instance-state-name'
    f1['Values'] = ['running']
    filters.append(f1)
    # print filters
    #rs = ec2.describe_instances(Filters=filters)
    rs = ec2.describe_instances()
    now = datetime.datetime.now(tzutc())
    lookback = datetime.timedelta(seconds=idle_period_secs)
    time_start = now - lookback

    # output report
    fout = open(outputfile, 'w')


    for r in rs['Reservations']:

        for i in r['Instances']:
            launch_time = i['LaunchTime']
            if is_in_autoscale_group(region, i['InstanceId']):
                continue
            age = now - launch_time
            if age < datetime.timedelta(seconds=idle_period_secs):
                print "Age of instance %s = %s, less than %s" %\
                      (i['InstanceId'], str(age), str(lookback))
                continue
            dim = [{'Name': 'InstanceId', 'Value': i['InstanceId']}]
            period = idle_period_secs - (idle_period_secs % 300)
            if period < 300:
                period = 300
            metric = c.get_metric_statistics(Period=period,
                                             StartTime=time_start,
                                             EndTime=now,
                                             MetricName='CPUUtilization',
                                             Namespace='AWS/EC2',
                                             Statistics=['Average'],
                                             Dimensions=dim)


            # print those metrics!!
            if metric['Datapoints']:
                average = metric['Datapoints'][0]['Average']
                print "Average for %s is %f. Minimum is %f" \
                      % (i['InstanceId'], average, minimum)
                if average < minimum:
                    print "We should terminate instance %s. Adding to report: shutdownlist.txt" % i['InstanceId']
                    fout.write(i['InstanceId']+'\n')
                    #
                    #  Want to just periodically run script and shut em down automatically?
                    # uncomment this block:
                    #
                    # inst = ec2res.Instance(i['InstanceId'])
                    # inst.stop()
                    # ----------------------------------------
    fout.close()
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True,
                        dest='region', default=None)
    parser.add_argument("--tag-key", required=False,
                        dest='tag_key', default='instance-purpose')
    parser.add_argument("--tag-values", required=False,
                        dest='tag_values', default='test')
    parser.add_argument("--idle-period-secs", required=False,
                        dest='idle_period_secs', type=int, default=86400)
    parser.add_argument("--minimum-utilization", required=False,
                        dest='minimum', type=float, default=0.05)
    parser.add_argument("--outputfile", dest='outputfile', required=False, default='shutdownlist.txt')



    result = parser.parse_args()
    find_idle_instances(region=result.region,
                        tag_key=result.tag_key,
                        tag_values=result.tag_values,
                        idle_period_secs=result.idle_period_secs,
                        minimum=result.minimum,
                        outputfile=result.outputfile)

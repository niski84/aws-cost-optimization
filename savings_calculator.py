import csv
#
# Takes the instances output from find_idle_instance.py
# coorlates with output from generate_csv_all_instance_tags.py
# uses the pricing from AWS on demand instances: https://aws.amazon.com/ec2/pricing/on-demand/
# and computes the cost savings per month and per year
#
#
shutdownlist = []
fshutdownlist = open("shutdownlist.txt")
for line in fshutdownlist.readlines():
    shutdownlist.append(line.strip())
csv_file = "cf3_tag_report.csv"

records = []
record = {}

prices=[]
prices.append({"type": "t2.nano", "price": "0.0059"})
prices.append({"type": "t2.micro", "price": "0.012"})
prices.append({"type": "t2.small", "price": "0.023"})
prices.append({"type": "t2.medium", "price": "0.047"})
prices.append({"type": "t2.large", "price": "0.094"})
prices.append({"type": "t2.xlarge", "price": "0.188"})
prices.append({"type": "t2.2xlarge", "price": "0.376"})
prices.append({"type": "m3.medium", "price": "0.05"})
prices.append({"type": "m3.2xlarge", "price": "0.133"})
prices.append({"type": "m3.large", "price": "0.067"})
prices.append({"type": "m4.large", "price": "0.1"})
prices.append({"type": "m4.xlarge", "price": ".2"})
prices.append({"type": "m4.2xlarge", "price": "0.4"})
prices.append({"type": "m4.4xlarge", "price": "0.8"})
prices.append({"type": "m4.10xlarge", "price": "2"})
prices.append({"type": "m4.16xlarge", "price": "3.2"})
prices.append({"type": "c3.large", "price": "0.105"})
prices.append({"type": "c3.xlarge", "price": "0.21"})
prices.append({"type": "c3.2xlarge", "price": "0.42"})
prices.append({"type": "c3.4xlarge", "price": "0.84"})
prices.append({"type": "c3.8xlarge", "price": "1.68"})
prices.append({"type": "c4.large", "price": "0.1"})
prices.append({"type": "c4.large", "price": "0.1"})
prices.append({"type": "c4.large", "price": "0.1"})
prices.append({"type": "c4.xlarge", "price": "0.199"})
prices.append({"type": "c4.2xlarge", "price": "0.398"})
prices.append({"type": "c4.4xlarge", "price": "0.796"})
prices.append({"type": "c4.4xlarge", "price": "1.591"})
prices.append({"type": "p2.xlarge", "price": "0.9"})
prices.append({"type": "p2.8xlarge", "price": "7.2"})
prices.append({"type": "p2.16xlarge", "price": "14.4"})
prices.append({"type": "x1.16xlarge", "price": "6.669"})
prices.append({"type": "x1.32xlarge", "price": "13.338"})
prices.append({"type": "r3.large", "price": "0.166"})
prices.append({"type": "r3.xlarge", "price": "0.333"})
prices.append({"type": "r3.2xlarge", "price": "0.665"})
prices.append({"type": "r3.4xlarge", "price": "1.33"})
prices.append({"type": "r3.8xlarge", "price": "2.66"})
prices.append({"type": "r4.large", "price": "0.133"})
prices.append({"type": "r4.xlarge", "price": "0.266"})
prices.append({"type": "r4.2xlarge", "price": "0.532"})
prices.append({"type": "r4.4xlarge", "price": "1.064 "})
prices.append({"type": "r4.8xlarge", "price": "2.128 "})
prices.append({"type": "r4.16xlarge", "price": "4.256"})
prices.append({"type": "i3.large", "price": "0.156 "})
prices.append({"type": "i3.xlarge", "price": "0.312"})
prices.append({"type": "i3.2xlarge", "price": "0.624"})
prices.append({"type": "i3.4xlarge", "price": "1.248"})
prices.append({"type": "i3.8xlarge", "price": "2.496 "})
prices.append({"type": "i3.16xlarge", "price": "4.992 "})
prices.append({"type": "d2.xlarge", "price": "0.69"})
prices.append({"type": "d2.2xlarge", "price": "1.38"})
prices.append({"type": "d2.4xlarge", "price": "2.76"})
prices.append({"type": "d2.8xlarge", "price": "5.52"})

cost = 0
total_cost_per_hour = 0
total_cost_per_month = 0

with open(csv_file) as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    for row in spamreader:
        record["instance_id"] = row[0]
        record["launch_time"] = row[1]
        record["type"] = row[2]
        records.append(record)

        cost = ""
        for shutdown in shutdownlist:
            if record["instance_id"] == shutdown:
                for price in prices:
                    if record["type"] == price["type"]:
                        cost = price["price"]

                print record["instance_id"] + " " + record["type"] + " " + "cost per month: " + str(float(cost)*24*30)
                total_cost_per_month = float(total_cost_per_month) + (float(cost)*24*30)

    print "cost savings per month: " + str(total_cost_per_month)
    print "cost savings per year: " + str(total_cost_per_month*12)

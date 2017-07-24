import os
from datetime import datetime


profiles_to_run= [
{'profile': '291341409612-predix-w2-cf3', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags.py'},
 {'profile': '704700539638-predix-cf2-w2', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags.py'},
 {'profile': '625444672796-apne-cf2', 'region': 'ap-northeast-1', 'which_report' : 'generate_csv_all_instance_tags.py'},
 {'profile': '011821064023-Power.Predix.East.2', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags_read_only.py'},
 {'profile': '867396380247-Power.Predix.East.3', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags_read_only.py'},
 {'profile': '548719943780=Masergy-PredixIO', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags.py'},
 {'profile': '124439511098-Predix-Data-Dev', 'region': 'us-west-2', 'which_report' : 'generate_csv_all_instance_tags.py'},
]

report_dir = "./reports/"+str(datetime.now().strftime('%Y-%m-%d-%H')+"/")
os.system("mkdir -p {0}".format(report_dir))

for profile in profiles_to_run:
    if 'read_only' not in profile['which_report']:
        cmd =  "python aws_tag_validation.py --dryrun=false --region={1} --profile={0}".format(profile['profile'],profile['region'])
        print cmd

    csv_name = profile['profile']+"_tag_report.csv"
    cmd = "python {2} --region={1} --profile={0} --output={3}".format(profile['profile'],profile['region'],profile['which_report'],report_dir+csv_name)
    print cmd
    #os.system("python generate_csv_all_instance_tags_read_only.py --profile {0}".format(profile))

    #os.system("open {0} -a \"Microsoft Excel\"".format(csv_name))
    cmd =  "open {0} -a \"Microsoft Excel\"".format(csv_name)
    print cmd


def unused():
    pass

# sample output:
#
# python aws_tag_validation.py --dryrun=False --region=us-west-2 --profile=291341409612-predix-w2-cf3
# python 291341409612-predix-w2-cf3 --region=us-west-2 --profile=generate_csv_all_instance_tags.py --output=./reports/2017-07-24-11/291341409612-predix-w2-cf3_tag_report.csv
# open 291341409612-predix-w2-cf3_tag_report.csv -a "Microsoft Excel"
# python aws_tag_validation.py --dryrun=False --region=us-west-2 --profile=704700539638-predix-cf2-w2
# python 704700539638-predix-cf2-w2 --region=us-west-2 --profile=generate_csv_all_instance_tags.py --output=./reports/2017-07-24-11/704700539638-predix-cf2-w2_tag_report.csv
# open 704700539638-predix-cf2-w2_tag_report.csv -a "Microsoft Excel"
# python aws_tag_validation.py --dryrun=False --region=ap-northeast-1 --profile=625444672796-apne-cf2
# python 625444672796-apne-cf2 --region=ap-northeast-1 --profile=generate_csv_all_instance_tags.py --output=./reports/2017-07-24-11/625444672796-apne-cf2_tag_report.csv
# open 625444672796-apne-cf2_tag_report.csv -a "Microsoft Excel"
# python 011821064023-Power.Predix.East.2 --region=us-west-2 --profile=generate_csv_all_instance_tags_read_only.py --output=./reports/2017-07-24-11/011821064023-Power.Predix.East.2_tag_report.csv
# open 011821064023-Power.Predix.East.2_tag_report.csv -a "Microsoft Excel"
# python 867396380247-Power.Predix.East.3 --region=us-west-2 --profile=generate_csv_all_instance_tags_read_only.py --output=./reports/2017-07-24-11/867396380247-Power.Predix.East.3_tag_report.csv
# open 867396380247-Power.Predix.East.3_tag_report.csv -a "Microsoft Excel"
# python aws_tag_validation.py --dryrun=False --region=us-west-2 --profile=548719943780=Masergy-PredixIO
# python 548719943780=Masergy-PredixIO --region=us-west-2 --profile=generate_csv_all_instance_tags.py --output=./reports/2017-07-24-11/548719943780=Masergy-PredixIO_tag_report.csv
# open 548719943780=Masergy-PredixIO_tag_report.csv -a "Microsoft Excel"
# python aws_tag_validation.py --dryrun=False --region=us-west-2 --profile=124439511098-Predix-Data-Dev
# python 124439511098-Predix-Data-Dev --region=us-west-2 --profile=generate_csv_all_instance_tags.py --output=./reports/2017-07-24-11/124439511098-Predix-Data-Dev_tag_report.csv
# open 124439511098-Predix-Data-Dev_tag_report.csv -a "Microsoft Excel"

# aws_tagging

## scripts in this repo:

- aws_tag_validation.py
    - Audits existing EC2 instances and adds NON_COMPLIANT_TAGGING if required_tags not found.
    - Designed to be run periodically (idempotent)
- generate_csv_all_instance_tags.py
    - generates report of all ec2 instances and their tags with special use of output from aws_tag_validation.py
- - generate_csv_all_instance_tags_read_only.py
-   - forked version of generate csv to remove dependency off aws_tag_validation.py running first.
- shutdown_ec2_list.py
    - shutdown a list of instances provided in text file
- find_idle_instances.py
    - generates reports of EC2 idle instances (avg cpu usage over last 5 mins less than .05% cpu)
    - outputs to /reports/shutdownlist.txt
- savings_calculator.py
    - Computes the cost savings per month and per year of shutting down idle instances identified in find_idle_instances.py
- AutoTag/template.json and *.docx
    - cloudformation template to autotag each instance with best guess of provisioner/owner
    - this functionality has been moved to a diff repo. (ported cloudformaiton to terraform):
        - https://github.svc.ice.gecis.io/pce-cap/tf_aws_autotag

# Why we are tagging

Most companies divide their costs for reporting by using separate accounts.  Lately the trend however is to make use of tagging. (Oct 2016 AWS upped tag limits from 10 to 50; concatonating tags is no longer a needed workaround)

But with so many provisioners within an environment, how can we enforce tag compliance?  Are we building up a hefty number of untagged or partially tagged instances? How do we resolve this?

This is.a two step problem. We have running instances that belong to owners that can not be impacted. We also have new instances being created that need a mechanism of tag enforcement.

For the first problem we need to identify the owners of images and work with them to get their tagging into compliance with standards set forth by XXXX.

The second problem of getting newly provisioned instances to have the correct nomenclature comes with an extra hurdle. Because there are many groups provisioning their own instances and tags, (~15 have been identified) we need a mechanism of keeping them all in sync.

The best way of doing this is to make the enforcement at a central location and code reusability.

For proposed method of cleanup and future work, have a look at the NC proposal document.


# Prerequisites:
    pip install -r requirements.txt

# How to use these script
usage: <script_name>.py [-h] profile region dryrun={true,false}

positional arguments:
  profile       AWS profile: cf3w2cfpoweruser
  region        AWS region: us-west-2
  {true,false}  Dry Run. defaults to True (dry run)

optional arguments:
  -h, --help    show this help message and exit

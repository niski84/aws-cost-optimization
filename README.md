# aws_tagging

## scripts in this repo:

- aws_tag_validation.py
    - Audits existing EC2 instances and adds NON_COMPLIANT_TAGGING if required_tags not found.
    - Designed to be run periodically (idempotent)
- generate_csv_all_instance_tags_read_only.py
    - Generate CSV report of all instances on instance attributes and cloudwatch metrics
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

# Prerequisites:
    pip install -r requirements.txt

# How to use these script
usage: script_name.py [-h]

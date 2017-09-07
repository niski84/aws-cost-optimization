#!/usr/bin/env python
#
#  Author: Nick Skitch (CAP team)
#  For Tagging Compliance.
prog_desc = "attach an inline polciy to all roles within an account"
#


import boto3
import json


def main():

    boto3.setup_default_session(profile_name='skunkworks')
    client = boto3.client('iam')
    policy_document = get_policy_body('required_tags.json')

    roles = get_roles(client)

    for role in roles:
        print "adding policy to role: {1}".format(policy_document,role)
        update_role(role,client,"required_tags",policy_document)

def get_policy_body(data_file):
    with open(data_file) as data_file:
        data = data_file.read()
    return data

def update_role(role_name, client,iam_policy_name,policy_document):
    response = client.put_role_policy(
    RoleName=role_name,
    PolicyName=iam_policy_name,
    PolicyDocument=policy_document
    )

    print response

def get_roles(client):
    client = boto3.client('iam')
    response = None
    role_names = []
    marker = None

    # By default, only 100 roles are returned at a time.
    # 'Marker' is used for pagination.
    while (response is None or response['IsTruncated']):
        # Marker is only accepted if result was truncated.
        if marker is None:
            response = client.list_roles()
        else:
            response = client.list_roles(Marker=marker)

        roles = response['Roles']
        for role in roles:
            print(role['Arn'])
            role_names.append(role['RoleName'])

        if response['IsTruncated']:
            marker = response['Marker']

    return role_names



if __name__ == "__main__":
    main()

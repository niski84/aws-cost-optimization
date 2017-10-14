#!/usr/bin/env python
import optparse
import sys

from boto.s3.connection import S3Connection

def sign(bucket, path, access_key, secret_key, https, expiry):
    c = S3Connection(access_key, secret_key)
    return c.generate_url(
        expires_in=long(expiry),
        method='GET',
        bucket=bucket,
        key=path,
        query_auth=True,
        force_http=(not https)
    )

if __name__ == '__main__':

    bucket_name = 'predix-tagging-compliance'
    filename = 'csv_reports/latest/latest_combined_accounts_ebs_report.csv'
    aws_access_key_id=''
    aws_secret_access_key=''

    # parser = optparse.OptionParser()
    # parser.add_option('-b', '--bucket', dest='bucket', help='S3 bucket containing the file')
    # parser.add_option('-p', '--path', dest='path', help='Path to the file (relative to the bucket)')
    # parser.add_option('-a', '--access-key', dest='access_key', help='Your AWS Access Key ID')
    # parser.add_option('-s', '--secret-key', dest='secret_key', help='Your AWS secret key')
    # parser.add_option('--no-https', dest='https', action='store_false', default=True, help='Disable serving over HTTPS')
    # parser.add_option('--expiry', dest='expiry', default='631138519', help='Expiry time, in seconds (defaults to two years)')
    #
    #options, args = parser.parse_args()

    # for opt in ('bucket', 'path', 'access_key', 'secret_key'):
    #     assert options.__dict__.get(opt), '%s is not optional' % opt


    print sign(
        bucket=bucket_name,
        path=filename,
        access_key=aws_access_key_id,
        secret_key=aws_secret_access_key,
        https=True,
        expiry=631138519
    )
    sys.exit(0)

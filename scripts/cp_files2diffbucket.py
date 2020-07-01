#!/usr/bin/env python3
'''
copy files from raw file bucket to processed file bucket
'''
import sys
import argparse
import boto3
from dcicutils.ff_utils import get_authentication_with_server, get_metadata
from functions import script_utils as scu


def get_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[scu.create_ff_arg_parser()],
    )
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    # initial set up
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    # bucket addresses
    ff_health = get_metadata('/health', auth)
    source_bucket = ff_health['file_upload_bucket']
    target_bucket = ff_health['processed_file_bucket']
    s3 = boto3.resource('s3')

    # get the uuids for the files
    query = 'type=FileVistrack'
    uids = scu.get_item_ids_from_args([query], auth, True)
    files2copy = [get_metadata(uid, auth).get('upload_key') for uid in uids]

    for file_key in files2copy:
        copy_source = {'Bucket': source_bucket, 'Key': file_key}
        try:
            # print(file_key + ' cp from ' + source_bucket + ' to ' + target_bucket)
            s3.meta.client.copy(copy_source, target_bucket, file_key)
        except Exception:
            print('Can not find file on source', file_key)
            continue
        print('{} file copied'.format(file_key))


if __name__ == '__main__':
    main()

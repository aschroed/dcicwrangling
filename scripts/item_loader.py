#!/usr/bin/env python3

import sys
import argparse
import json
from datetime import datetime
from dcicutils.ff_utils import (
    get_authentication_with_server,
    post_metadata,
)
from dcicwrangling.functions.script_utils import create_ff_arg_parser, convert_key_arg_to_dict
''' Will attempt to load data from a file into the database
    The file can be a simple list of json items in which case you need to specify an item type
    with the --itype option (file created by generate_ontology is like this)
    or the file can specify a dictionary with item types as keys and list of jsons as values
'''


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of item jsons try to load into database',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    parser.add_argument('--itype',
                        help="The item type to load if not specified in the file by dict key")
    args = parser.parse_args()
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def load(auth, itype, item_list):
    list_length = len(item_list)
    store = {itype: item_list}
    payload = {'store': store, 'overwrite': True}
    if 'localhost' in auth.get('server', ''):
        payload['config_uri'] = 'development.ini'
    try:
        res = post_metadata(payload, 'load_data', auth)
    except Exception as e:
        print("PROBLEM WITH POST")
        print(e)


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    if not args.dbupdate:
        print("DRY RUN - use --dbupdate to update the database")
    with open(args.infile) as ifile:
        item_store = json.loads(ifile.read())
        if not args.itype:
            if not isinstance(item_store, dict):
                print("File is not in correct format")
                sys.exit(1)
            for itype, items in item_store.items():
                if args.dbupdate:
                    load(auth, itype, items)
                else:
                    print('DRY RUN - would try to load {} {} items'.format(len(items), itype))
        else:
            if not isinstance(item_store, list):
                print("File is not in correct format")
                sys.exit(1)
            if args.dbupdate:
                load(auth, args.itype, item_store)
            else:
                print('DRY RUN - would try to load {} {} items'.format(len(item_store), args.itype))


if __name__ == '__main__':  # pragma: no cover
    main()

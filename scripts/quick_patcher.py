#!/usr/bin/env python3
''' This can be used to directly patch items using a json formatted payload
    the input file - 1 line per item uuid<tab>json payload
    useful for patching attributions
'''

import sys
import argparse
import json
from datetime import datetime
from dcicutils.ff_utils import fdn_connection
from dcicutils.submit_utils import patch_FDN
from dcicwrangling.scripts.script_utils import create_ff_arg_parser


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of ontology term jsons (one per line) load into db',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    args = parser.parse_args()
    return args


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        connection = fdn_connection(args.keyfile, keyname=args.key)
    except Exception as e:
        print("Connection failed")
        sys.exit(1)

    # assumes a single line corresponds to json for single term
    if not args.dbupdate:
        print("DRY RUN - use --dbupdate to update the database")
    with open(args.infile) as items:
        for i in items:
            [iid, payload] = [t.strip() for t in i.split('\t')]
            payload = json.loads(payload)
            if args.dbupdate:
                e = patch_FDN(iid, connection, payload)
            else:
                print("DRY RUN\n\tPATCH: ", iid, " TO\n", payload)
                e = {'status': 'success'}

            status = e.get('status')
            if status and status == 'success':
                print(status)
            else:
                print('FAILED', e)

    end = datetime.now()
    print("FINISHED - START: ", str(start), "\tEND: ", str(end))


if __name__ == '__main__':
        main()

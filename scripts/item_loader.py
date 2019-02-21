#!/usr/bin/env python3

import sys
import argparse
import json
from datetime import datetime
from dcicutils.ff_utils import (
    get_authentication_with_server,
    get_metadata,
    patch_metadata,
    post_metadata,
)
from dcicwrangling.functions.script_utils import create_ff_arg_parser, convert_key_arg_to_dict
''' Generalized script to load items given a file with a single json per line
    NOTE: will not do any phasing
'''


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of item jsons (one per line) load into db',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    parser.add_argument('--id_field',
                        default='uuid',
                        help="the name of a field to use as an identifier - default is uuid")
    parser.add_argument('--itype',
                        help="Item type using schema naming convention eg. ontology_term - not required for patching")
    args = parser.parse_args()
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def camel_case(name):
    return ''.join(x for x in name.title() if not x == '_')


def get_id_value(field, item):
    val = item.get(field)
    if field == 'aliases':
        try:
            return val[0]
        except IndexError:
            return None
    return val


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    print("Running on {}".format(auth.get('server')))
    # assumes a single line corresponds to json for single term
    if not args.dbupdate:
        print("DRY RUN - use --dbupdate to update the database")
    itype = None
    if args.itype:
        itype = args.itype
    labs = {}
    awards = {}
    with open(args.infile) as items:
        for i in items:
            i = i.strip()
            if not i or i.startswith('#'):
                continue
            item = json.loads(i)
            labs.update({item.get('lab'): None})
            awards.update({item.get('award'): None})
        print("Labs")
        for l in labs.keys():
            print(l)
        print("Awards")
        for a in awards.keys():
            print(a)
        exit()
        for i in items:
            id_tag = get_id_value(args.id_field, item)
            if id_tag is None:
                print("No Identifier for ", item)
            else:
                tid = ''
                if itype:
                    tid = '/' + itype + '/'
                tid += id_tag
                try:
                    dbterm = get_metadata(tid, auth)
                except:  # noqa
                    dbterm = None
                op = ''
                if dbterm and 'Error' not in dbterm.get('@type'):
                    if itype and camel_case(itype) not in dbterm.get('@type'):
                        print("Item is not same type as existing one in db")
                        continue
                    if args.dbupdate:
                        e = patch_metadata(item, dbterm["uuid"], auth)
                    else:
                        e = {'status': 'dry run'}
                    op = 'PATCH'
                else:
                    if args.dbupdate:
                        e = post_metadata(item, camel_case(itype), auth)
                    else:
                        e = {'status': 'dry run'}
                    op = 'POST'
                status = e.get('status')
                if status and status == 'dry run':
                    print(op, status)
                elif status and status == 'success':
                    print(op, status, e['@graph'][0]['uuid'])
                else:
                    print('FAILED', tid, e)

    end = datetime.now()
    print("FINISHED - START: ", str(start), "\tEND: ", str(end))


if __name__ == '__main__':  # pragma: no cover
    main()

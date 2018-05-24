#!/usr/bin/env python3
'''
Given a list of item IDs will fetch the items or the fields of those items
specified in the --fields parameter)
'''
import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, get_metadata
from dcicwrangling.scripts import script_utils as scu


def get_args():
    parser = argparse.ArgumentParser(
        parents=[scu.create_input_arg_parser(), scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--fields',
                        nargs='+',
                        help="The item fields to retrieve/report.")
    parser.add_argument('--noid',
                        action='store_true',
                        default='False')

    return parser.parse_args()


def main():  # pragma: no cover
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    id_list = scu.get_item_ids_from_args(args.input, auth, args.search)
    if args.fields:
        fields = args.fields

        header = '#id\t' + '\t'.join(fields)
        if args.noid is True:
            header = header.replace('#id\t', '#')
        print(header)
    for iid in id_list:
        res = get_metadata(iid, auth)
        if args.fields:
            line = ''
            for f in fields:
                val = res.get(f)
                if isinstance(val, list):
                    for v in val:
                        v = str(v)
                        vs = v + ', '
                    val = vs
                    if val.endswith(', '):
                        val = val[:-2]
                line = line + str(val) + '\t'
            if args.noid == 'False':
                line = iid + '\t' + line
            print(line)
        else:
            if args.noid is True:
                print(res)
            else:
                print(iid, '\t', res)


if __name__ == '__main__':
        main()

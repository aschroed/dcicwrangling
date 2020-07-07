#!/usr/bin/env python3
'''
Given a list of item IDs will fetch the items or the fields of those items
specified in the --fields parameter)
'''
import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, get_metadata
from functions import script_utils as scu


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
                        default='False',
                        help="By default the id provided is the first column of output - this flag removes that column")

    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    print('#', auth.get('server'))
    id_list = scu.get_item_ids_from_args(args.input, auth, args.search)
    if args.fields:
        fields = args.fields

        header = '#id\t' + '\t'.join(fields)
        if args.noid is True:
            header = header.replace('#id\t', '#')
        print(header)
    problems = []
    for iid in id_list:
        try:
            res = get_metadata(iid, auth, add_on='frame=object')
        except Exception:
            problems.append(iid)
            continue

        if args.fields:
            line = ''
            # counts = {}
            for f in fields:
                val = res.get(f)
                # if val is not None:  # added in for specific use case
                if isinstance(val, dict):
                    val = val.get('uuid')
                elif isinstance(val, list):
                    # counts[f] = len(val)  # added in for specific use case
                    # if len(counts) > 1:
                    #     print(iid, '\t', counts)
                    # else:
                    #     cnt = list(counts.values())[0]
                    #     if cnt > 1:
                    #         print(iid, '\t', cnt)
                    vs = ''
                    for v in val:
                        if isinstance(v, dict):
                            v = v.get('uuid')
                        else:
                            v = str(v)
                        vs = vs + v + ', '
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
    if problems:
        print('THERE WAS A PROBLEM GETTING METADATA FOR THE FOLLOWING:')
        for p in problems:
            print(p)


if __name__ == '__main__':
    main()

import sys
import argparse
from dcicutils.ff_utils import fdn_connection
from dcicutils.submit_utils import patch_FDN
from dcicwrangling.scripts import script_utils as scu


def get_args():
    parser = argparse.ArgumentParser(
        parents=[scu.create_input_arg_parser(), scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('field',
                        help="The field to update.")
    parser.add_argument('value',
                        help="The value(s) to update. Array fields need \"''\" surround \
                        even if only a single value i.e. \"'value here'\" or \"'v1' 'v2'\"")
    parser.add_argument('--isarray',
                        default=False,
                        action='store_true',
                        help="Field is an array.  Default is False \
                        use this so value is correctly formatted even if only a single value")
    return parser.parse_args()


def main():
    args = get_args()
    try:
        connection = fdn_connection(args.keyfile, keyname=args.key)
    except Exception:
        print("Connection failed")
        sys.exit(1)

    id_list = scu.get_item_ids_from_args(args.input, connection, args.search)
    val = args.value
    if args.isarray:
        val = val.split("'")[1::2]
    for iid in id_list:
        print("PATCHING", iid, "to", args.field, "=", val)
        if (args.dbupdate):
            # do the patch
            res = patch_FDN(iid, connection, {args.field: val})
            if res['status'] == 'success':
                print("SUCCESS!")
            else:
                print("FAILED TO PATCH", iid, "RESPONSE STATUS", res['status'], res['description'])
                # print(res)


if __name__ == '__main__':
    main()

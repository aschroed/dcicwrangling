import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, patch_metadata
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
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    itemids = scu.get_item_ids_from_args(args.input, auth, args.search)
    val = args.value
    if args.isarray:
        val = val.split("'")[1::2]
    for iid in itemids:
        print("PATCHING", iid, "to", args.field, "=", val)
        if (args.dbupdate):
            # do the patch
            res = patch_metadata({args.field: val}, iid, auth)
            if res['status'] == 'success':
                print("SUCCESS!")
            else:
                print("FAILED TO PATCH", iid, "RESPONSE STATUS", res['status'], res['description'])
                # print(res)


if __name__ == '__main__':
    main()

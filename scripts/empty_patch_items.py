import sys
import argparse
from dcicutils import ff_utils as ff
from dcicwrangling.scripts import script_utils as scu


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Provide a search query suffix and get a list of item uuids',
        parents=[scu.create_ff_arg_parser(), scu.create_input_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    try:
        auth = ff.get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    itemids = scu.get_item_ids_from_args(args.input, auth, True)
    for itemid in itemids:
        print("Touching ", itemid)
        if args.dbupdate:
            ff.patch_metadata({}, itemid, auth)
        else:
            print('dry run!')

if __name__ == '__main__':
    main()

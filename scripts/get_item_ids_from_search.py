import sys
import argparse
from dcicutils import ff_utils as ff
from dcicwrangling.scripts import script_utils as scu


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Provide a search query suffix and get a list of item uuids',
        parents=[scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('query',
                        help="A search string \
                        eg. type=Biosource&biosource_type=primary cell")
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    try:
        auth = ff.get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    itemids = scu.get_item_ids_from_args([args.query], auth, True)
    for itemid in itemids:
        print(itemid)


if __name__ == '__main__':
    main()

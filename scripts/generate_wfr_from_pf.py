import sys
import argparse
from datetime import datetime
from dcicutils.ff_utils import get_authentication_with_server, get_metadata, post_metadata
from functions import script_utils as scu
'''Generate provenance workflow_runs for processed files using the
    information in the 'produced_from' field.
    input is a list of file ids or a search for the files.
'''


def get_args(args):
    parser = argparse.ArgumentParser(
        parents=[scu.create_ff_arg_parser(), scu.create_input_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--workflow',
                        default="bef50397-4d72-4ed1-9c78-100e14e5c47f",
                        help="The uuid of the workflow to use to generate the run \
                              default is File Provenance Workflow"
                        )

    args = parser.parse_args(args)
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def _filter_none(my_list):
    nl = [li for li in my_list if li is not None]
    if len(nl) != len(my_list):
        print('WARNING: None values found in your list')
    return nl


def get_attribution(items):
    award = lab = None
    for i in items:
        award = i.get('award')
        lab = i.get('lab')
        if award and lab:
            try:
                award = award.get('uuid')
                lab = lab.get('uuid')
            except AttributeError:
                pass
            return award, lab
    # default to 4dn-dcic award and lab
    return 'b0b9c607-f8b4-4f02-93f4-9895b461334b', '828cd4fe-ebb0-4b36-a94a-d2e3a36cc989'


def create_wfr_meta_only_json(auth, workflow, inputs, outputs, alias=None, description=None):
    '''provide input file(s), output file(s), optional alias,
       optional description builds a metadata only workflow_run json
       currently designed for file tracing so does not do quality metrics
       or deal with arguments other than Input file and Output processed file'''
    workflow = scu.get_item_if_you_can(auth, workflow)
    if workflow.get('uuid') is None:
        return None
    infiles = _filter_none([scu.get_item_if_you_can(auth, i) for i in inputs])
    outfiles = _filter_none([scu.get_item_if_you_can(auth, o) for o in outputs])
    now = str(datetime.now())
    if alias is None:
        alias = '4dn-dcic-lab:' + workflow.get('name') + '_run_' + now.replace(':', '-').replace(' ', '-')
    wfr_title = workflow.get('title') + ' run on ' + now

    award, lab = get_attribution(infiles + outfiles + [workflow])

    wfr_json = {
        'workflow': workflow.get('uuid'),
        'aliases': [alias],
        'award': award,
        'lab': lab,
        'status': 'in review by lab',
        'title': wfr_title,
        'run_status': 'complete',
        'metadata_only': True
    }

    if description is not None:
        wfr_json['description'] = description

    args = workflow.get('arguments')
    input_files = []
    output_files = []
    if args:
        for arg in args:
            argname = arg.get('workflow_argument_name')
            if arg.get('argument_type') == 'Input file':
                # build the needed inputs
                for i, inf in enumerate(infiles):
                    input_files.append(
                        {
                            'workflow_argument_name': argname,
                            'value': inf.get('uuid'),
                            'ordinal': i + 1
                        }
                    )
            if arg.get('argument_type') == 'Output processed file':
                for outf in outfiles:
                    output_files.append(
                        {
                            'workflow_argument_name': argname,
                            'value': outf.get('uuid'),
                            'workflow_argument_format': outf.get('file_format').get('uuid'),
                            'type': 'Output processed file'
                        }
                    )

    if input_files:
        wfr_json['input_files'] = input_files
    if output_files:
        wfr_json['output_files'] = output_files
    return wfr_json


def main():
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    dryrun = not args.dbupdate

    file_list = scu.get_item_ids_from_args(args.input, auth, args.search)
    wf_data = get_metadata(args.workflow, auth)
    for f in file_list:
        file_info = get_metadata(f, auth)
        parents = file_info.get('produced_from')
        if parents:
            inputs = []
            for p in parents:
                inputs.append(get_metadata(p, auth))
            wfr_json = create_wfr_meta_only_json(auth, wf_data, inputs, [file_info])
            if dryrun:
                print('DRY RUN -- will post')
                print(wfr_json)
            else:
                res = post_metadata(wfr_json, 'workflow_run_awsem', auth)
                print(res)


if __name__ == '__main__':  # pragma: no cover
    main()

#!/usr/bin/env python3
import sys
import argparse
import requests
import copy
from dcicutils.ff_utils import get_authentication_with_server, get_metadata, post_metadata
from dcicwrangling.scripts import script_utils as scu
'''
Get all files (processed) of a type from a dataset search from encode
eg. all bigWig fold change files from H1-hESC and HFFc6 (HFF) cells

Fields of the file_vistrack to populate

"aliases" - need for tracking so can upload
"description" - file specific (need to construct)
"file_format" - bw (use uuid - fetch it from fourfront?)
"file_type" - fold change values
"file_classification" - visualization
"genome_assembly" - GRCh38
"biosource" - map to our uuids
"dataset_description"
"dataset_type"
"replicate_identifiers"
"project_lab"
"project_release_date"
"dbxrefs" - both the file and dataset encode accessions

need to get download_url to alias map
'''


def get_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[scu.create_ff_arg_parser()],
    )
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def enc_data_from_tsv_url(uri, key=None):
    ''' Takes a uri with a report.tsv request to encode and returns either:
        1. A dictionary keyed by the provided key param and vals are dict of field:val
        2. A list of dicts of field:val pairs
    '''
    encres = requests.get(uri)
    lines = [l.strip() for l in encres.text.split('\n')]
    # import pdb; pdb.set_trace()
    lines.pop(0)  # get rid of first line with search
    fieldnames = lines.pop(0).split('\t')
    if key is not None and key not in fieldnames:
        print("ERROR - Provided key {} is not found in the metadata".format(key))
        return None
    datalist = [dict(zip(fieldnames, l.split('\t'))) for l in lines]
    if key is None:
        return datalist
    return {d.get(key): d for d in datalist}


def get_ff_file_formats(auth):
    query = 'type=FileFormat&status=released'
    ffids = scu.get_item_ids_from_args([query], auth, True)
    return {get_metadata(f, auth).get('file_format'): f for f in ffids}


def generate_expt_description(expt):
    '''use the available metadata to generate a description
        something like "NRF1 ChIP-seq on human H1-hESC"
    '''
    target = expt.get('Target label', '')
    assay = expt.get('Assay Nickname', '')
    if not assay:
        assay = expt.get('Assay Type', '')
    biosample = expt.get('Biosample summary', '')
    if not biosample:
        biosample = expt.get('Biosample', '')
    desc = '{t} {a} on {b}'.format(t=target, a=assay, b=biosample)
    if desc.startswith(' '):
        desc = desc.lstrip()
    return desc


def generate_file_desc(meta, expt, format):
    '''meta is the file metadata so far, expt is the encode expt info
        which we use to generate a standard expt description which may be
        different from the dataset description (to deal with lab consistently)
        format is 'bigWig'
    '''
    filedesc = format + ' file of ' + meta.get('file_type')
    expdesc = generate_expt_description(expt)
    lab = meta.get('project_lab', 'ENCODE DCC')
    filedesc = filedesc + ' for {exp} from {lab}'.format(exp=expdesc, lab=lab)
    repinfo = meta.get('replicate_identifiers')
    if repinfo is not None:
        if len(repinfo) > 1:
            rep = 'merged replicates'
        else:
            rep = 'unreplicated'
        filedesc = filedesc + ' ({rep})'.format(rep=rep)
    return filedesc


def main():  # pragma: no cover
    # initial set up
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    enc_dcc_lab = '/labs/encode-dcc-lab/'
    enc_award = '/awards/encode-award/'
    fourdn_formats = get_ff_file_formats(auth)
    enc24dnformat = {'bigWig': 'bw'}
    biomap = {'HFFc6': '4DNSRC6ZVYVP', 'H1-hESC': '4DNSRV3SKQ8M'}
    ftmap = {'fold change over control': 'fold change over control'}

    enc_expt_tsv_uri = (
        'https://www.encodeproject.org/report.tsv?'
        'type=Experiment&status=released&assembly=GRCh38&'
        'biosample_term_name=H1-hESC&biosample_term_name=HFFc6&'
        'field=%40id&field=accession&field=assay_term_name&field=assay_title&'
        'field=biosample_term_name&field=biosample_summary&'
        'field=description&field=lab.title&'
        'field=award.project&field=files.%40id&field=date_released&'
        'field=replicates.biological_replicate_number&'
        'field=replicates.technical_replicate_number&'
        'field=alternate_accessions&field=target.label')
    enc_file_tsv_uri = (
        'https://www.encodeproject.org/report.tsv?'
        'type=File&status=released&assembly=GRCh38&file_type=bigWig&'
        'output_type=fold+change+over+control&no_file_available=false&'
        'field=%40id&field=title&field=accession&field=dataset&field=assembly&'
        'field=technical_replicates&field=biological_replicates&field=file_format&'
        'field=file_type&field=file_format_type&field=file_size&field=href&'
        'field=output_category&field=output_type&field=lab&'
        'field=date_created&field=status&field=restricted&'
        'field=md5sum&field=file_size'
    )
    enc_expts = enc_data_from_tsv_url(enc_expt_tsv_uri, 'Accession')
    enc_files = enc_data_from_tsv_url(enc_file_tsv_uri, 'Accession')

    vistracks = {}
    for eacc, expt in enc_expts.items():
        shared_metadata = {
            'lab': enc_dcc_lab,
            'award': enc_award,
            'dataset_description': expt.get('Description', None),
            'dataset_type': expt.get('Assay Type', None),
            'project_lab': expt.get('Lab', None),
            'project_release_date': expt.get('Date released', None),
            'dbxrefs': [eacc],
            'biosource': biomap.get(expt.get('Biosample')),
            'genome_assembly': 'GRCh38',
            'file_classification': 'visualization',
            'assay_info': expt.get('Target label', None)
        }

        # do some checking and construction of a description if not present
        if shared_metadata.get('biosource') is None:
            if eacc is None:
                continue
            print("Experiment %s lacks a Biosample???" % eacc)
            continue
        if not shared_metadata.get('dataset_description'):
            shared_metadata['dataset_description'] = generate_expt_description(expt)

        expt_files = expt.get('Files', '')
        expt_files = [f.strip() for f in expt_files.split(',')]
        expt_files = [f.replace('/files/', '')[:-1] for f in expt_files]

        # if there are multiple files sort out the replicate info
        # this is hacky should be re-done
        interesting_files = [fid for fid in expt_files if fid in enc_files]
        facc = None
        for f in interesting_files:
            efile = enc_files.get(f)
            bioreps = efile.get('Biological replicates')
            if bioreps is not None and ',' in bioreps:
                facc = f

        if not facc:
            if len(interesting_files) == 1:
                facc = interesting_files[0]
            else:
                # there are some datasets ie. DNase-seq and RNA-seq that don't have files
                # with right data type
                # print("Problem resolving replicates for {}".format(eacc))
                continue

        vistrack_meta = copy.deepcopy(shared_metadata)
        efile = enc_files.get(facc)
        vistrack_meta['dbxrefs'].append(facc)
        alias = 'encode-dcc-lab:' + facc
        vistrack_meta['aliases'] = [alias]
        encformat = efile.get('File Format')
        ff = fourdn_formats.get(enc24dnformat.get(encformat))
        vistrack_meta['file_format'] = ff
        vistrack_meta['file_type'] = ftmap.get(efile.get('Data type', None), None)
        # add replicate info
        rep_str = efile.get('Technical replicates')
        if rep_str is not None:
            vistrack_meta['replicate_identifiers'] = []
            reps = [r.strip() for r in rep_str.split(',')]
            for rep in reps:
                bio, tec = rep.split('_')
                repstring = 'Biorep ' + bio + ' Techrep ' + tec
                vistrack_meta['replicate_identifiers'].append(repstring)
        # make a nice file description based on available meta
        vistrack_meta['description'] = generate_file_desc(vistrack_meta, expt, encformat)
        vistrack = {k: v for k, v in vistrack_meta.items() if v}
        if facc not in vistracks:
            vistracks[facc] = {
                'meta': vistrack,
                'download': {
                    'uri': efile.get('Download URL'),
                    'file_size': efile.get('File size'),
                    'md5': efile.get('MD5sum')
                }
            }
        else:
            print("We've seen this file %s already" % facc)

    # create metadata items
    for a, info in vistracks.items():
        payload = info.get('meta')
        print('Will post\n', payload)
        if args.dbupdate is True:
            try:
                res = post_metadata(payload, 'file_vistrack', auth)
                print(res.get('status'))
            except Exception as e:
                print(e)

    # output to look at
    # header = False
    # fsize = {}
    # for acc, info in vistracks.items():
    #     fsize[acc] = int(info.get('download').get('file_size'))
    # for k in sorted(fsize, key=fsize.get, reverse=True):
    #     print(k, fsize[k])
    #     # meta = info.get('meta')
    #     # if not header:
    #     #    print('\t'.join(meta.keys()))
    #     #    header = True
    #     # print('\t'.join(['None' if v is None else '; '.join(v) if isinstance(v, list) else v for v in meta.values()]))


if __name__ == '__main__':
    main()

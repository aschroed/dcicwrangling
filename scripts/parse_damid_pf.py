#!/usr/bin/env python3
import sys
import argparse
import xlrd
import datetime
from dcicutils.ff_utils import (
    get_authentication_with_server,
    patch_metadata, search_metadata)
from functions import script_utils as scu
'''
Parsing damid processed file worksheet to generate the various bins
of other processed files
'''


def reader(filename, sheetname=None):
    """Read named sheet or first and only sheet from xlsx file.
        from submit4dn import_data"""
    book = xlrd.open_workbook(filename)
    if sheetname is None:
        sheet, = book.sheets()
    else:
        try:
            sheet = book.sheet_by_name(sheetname)
        except xlrd.XLRDError:
            print(sheetname)
            print("ERROR: Can not find the collection sheet in excel file (xlrd error)")
            return
    datemode = sheet.book.datemode
    for index in range(sheet.nrows):
        yield [cell_value(cell, datemode) for cell in sheet.row(index)]


def cell_value(cell, datemode):
    """Get cell value from excel.
        from submit4dn import_data"""
    # This should be always returning text format if the excel is generated
    # by the get_field_info command
    ctype = cell.ctype
    value = cell.value
    if ctype == xlrd.XL_CELL_ERROR:  # pragma: no cover
        raise ValueError(repr(cell), 'cell error')
    elif ctype == xlrd.XL_CELL_BOOLEAN:
        return str(value).upper().strip()
    elif ctype == xlrd.XL_CELL_NUMBER:
        if value.is_integer():
            value = int(value)
        return str(value).strip()
    elif ctype == xlrd.XL_CELL_DATE:
        value = xlrd.xldate_as_tuple(value, datemode)
        if value[3:] == (0, 0, 0):
            return datetime.date(*value[:3]).isoformat()
        else:  # pragma: no cover
            return datetime.datetime(*value).isoformat()
    elif ctype in (xlrd.XL_CELL_TEXT, xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return value.strip()
    raise ValueError(repr(cell), 'unknown cell type')  # pragma: no cover


def get_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[scu.create_ff_arg_parser(), scu.create_input_arg_parser()],
    )
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    # initial set up
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    clines = ['K562', 'Hap1', 'HCT116', 'RPE']
    cline2name = {'Hap1': 'HAP-1', 'RPE': 'RPE-hTERT'}
    expts = ['LMNB1', 'Dam']
    reps = ['_r1_', '_r2_', 'combined']
    bins = ['gatc', '1kb', '2kb', '5kb', '10kb', '20kb', '25kb', '50kb', '80kb', '100kb', '250kb', 'not_binned']
    bins.reverse()

    supplementary = {cl: {e: {r: {b: [] for b in bins} for r in reps} for e in expts} for cl in clines}
    processed = {cl: {e: {r: [] for r in reps} for e in expts} for cl in clines}
    other_files = []
    # this if for parsing excel but could use fourfront query
    infile = args.input[0]
    query = None
    if len(args.input) > 1:
        query = args.input[1]

    row = reader(infile, sheetname='FileProcessed')
    fields = next(row)
    fields = [f.replace('*', '') for f in fields]
    types = next(row)
    fields.pop(0)
    types.pop(0)
    for values in row:
        pf_found = False
        if values[0].startswith('#'):
            continue
        values.pop(0)

        c = None
        e = None
        r = None
        b = None
        meta = dict(zip(fields, values))
        desc = meta.get('description')
        info = (meta.get('aliases'), desc)
        for cl in clines:
            if cl in desc:
                c = cl
                break
        for ex in expts:
            if ex in desc:
                e = ex
                break
        for rep in reps:
            if rep in desc:
                r = rep
                break
        if r is None:
            r = 'combined'
        if 'mapped reads' in desc:
            if not c or not e or not r:
                other_files.append(info)
            else:
                processed[c][e][r].append(info)
            continue
        for bin in bins:
            if bin in desc:
                b = bin
                if b == '5kb':
                    if (meta.get('file_type') == 'normalized counts' and meta.get('file_format') == 'bw') or (
                            meta.get('file_type') == 'LADs' and meta.get('file_format') == 'bed'):
                        processed[c][e][r].append(info)
                        pf_found = True
                break
        if pf_found:
            pf_found = False
            continue
        elif c and e and r and b:
            supplementary[c][e][r][b].append(info)
        elif c and e and r:
            if 'mapped reads' in desc:
                processed[c][e][r].append(info)
            else:
                supplementary[c][e][r]['not_binned'].append(info)
        else:
            other_files.append(info)

    # get ff esets and add correct bins to it
    if query is not None:
        esets = search_metadata(query, auth)
        for eset in esets:
            repset_uuid = eset.get('uuid')
            refexp = eset.get('experiments_in_set')[0]
            # import pdb; pdb.set_trace()
            cell_line = None
            expt = 'Dam'
            ename = 'Dam-only'
            bsum = refexp.get('biosample').get('biosource_summary')
            for c in clines:
                c2chk = cline2name.get(c)
                if c2chk is None:
                    c2chk = c
                if c2chk in bsum:
                    cell_line = c
                    break
            ecat = refexp.get('experiment_categorizer').get('value')
            if 'Lamin-B1' in ecat:
                expt = 'LMNB1'
                ename = 'Lamin-B1'

            # now we have enough to add repset specifics
            repset_pfs = processed.get(cell_line).get(expt).get('combined')
            patch = {
                'processed_files': [pf[0] for pf in repset_pfs],
                'other_processed_files': []
            }
            repset_others = supplementary.get(cell_line).get(expt).get('combined')
            datasetstr = 'DAM ID seq {bio} {expt} Dataset.'.format(bio=c2chk, expt=ename)
            for bin, files in repset_others.items():
                if not files:
                    continue
                if bin == 'not_binned':
                    title = 'Other files - non-binned'
                    desc = 'Non-bin specific files for the {}'.format(datasetstr)
                elif bin == '5kb':
                    title = 'Additional 5 kb binned files'
                    desc = 'Additional files associated with the 5 kb bin size processing of data for the {}'.format(datasetstr)
                else:
                    if bin == 'gatc':
                        bname = bin.upper()
                    else:
                        bname = bin.replace('kb', ' kb')
                    title = bname + ' binned files'
                    desc = 'The files associated with the {bin} bin size processing of data for the {ds}'.format(bin=bname, ds=datasetstr)
                patch['other_processed_files'].append(
                    {'title': title, 'description': desc, 'type': 'supplementary', 'files': [f[0] for f in files]}
                )
            if not patch.get('processed_files'):
                del patch['processed_files']
            if not patch.get('other_processed_files'):
                del patch['other_processed_files']
            if not patch:
                pass
            else:
                print(repset_uuid, '\n', patch, '\n\n')
                if args.dbupdate:
                    try:
                        res = patch_metadata(patch, repset_uuid, auth)
                        print(res.status)
                    except Exception:
                        print("Can't patch {iid} with\n\t{p}".format(iid=repset_uuid, p=patch))

            reps = eset.get('replicate_exps')
            for rep in reps:
                # experiment specific files
                repno = str(rep.get('bio_rep_no'))
                repuuid = rep.get('replicate_exp').get('uuid')
                reptag = '_r' + repno + '_'
                exprep_pfs = processed.get(cell_line).get(expt).get(reptag)
                reppatch = {
                    'processed_files': [epf[0] for epf in exprep_pfs],
                    'other_processed_files': []
                }
                repexp_others = supplementary.get(cell_line).get(expt).get(reptag)
                expstr = 'DAM ID seq {bio} {expt} Replicate {no}.'.format(bio=c2chk, expt=ename, no=repno)
                for bin, files in repexp_others.items():
                    if bin == 'not_binned':
                        title = 'Other files - non-binned'
                        desc = 'Non-bin specific files for the {}'.format(expstr)
                    elif bin == '5kb':
                        title = 'Additional 5 kb binned files'
                        desc = 'Additional files associated with the 5 kb bin size processing of data for the {}'.format(expstr)
                    else:
                        if bin == 'gatc':
                            bname = bin.upper()
                        else:
                            bname = bin.replace('kb', ' kb')
                        title = bname + ' binned files'
                        desc = 'The files associated with the {bin} bin size processing of data for the {ds}'.format(bin=bname, ds=expstr)
                    reppatch['other_processed_files'].append(
                        {'title': title, 'description': desc, 'type': 'supplementary', 'files': [f[0] for f in files]}
                    )
                if not reppatch.get('processed_files'):
                    del reppatch['processed_files']
                if not reppatch.get('other_processed_files'):
                    del reppatch['other_processed_files']
                if not reppatch:
                    continue
                else:
                    newpatch = [opf for opf in reppatch.get('other_processed_files') if opf.get('files')]
                    reppatch['other_processed_files'] = newpatch

                    print(repuuid, '\n', reppatch, '\n\n')
                    if args.dbupdate:
                        try:
                            res = patch_metadata(reppatch, repuuid, auth)
                            if res.get('status') == 'success':
                                print('SUCCESS')
                            else:
                                print('unexpected response\n', res)
                        except Exception:
                            print("Can't patch {iid} with\n\t{p}".format(iid=repuuid, p=reppatch))


if __name__ == '__main__':
    main()

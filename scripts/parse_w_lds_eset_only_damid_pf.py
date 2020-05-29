#!/usr/bin/env python3
import sys
import argparse
import xlrd
import datetime
import re
from dcicutils.ff_utils import (
    get_authentication_with_server,
    patch_metadata, search_metadata,
    get_metadata)
from dcicwrangling.functions import script_utils as scu
'''
Parsing damid processed file worksheet to generate the various bins
of other processed files

This variation uses the information from the linked_dataset column
that only contains replicate set aliases - will need to tweak if expt
aliases are provided - currently the bin to use for processed files
is specified in 2 places - is_processed_bin and create_patch functions
should be made a constant or param to supply
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


def extract_rows(infile):
    data = []
    row = reader(infile, sheetname='FileProcessed')
    fields = next(row)
    fields = [f.replace('*', '') for f in fields]
    types = next(row)
    fields.pop(0)
    types.pop(0)
    for values in row:
        if values[0].startswith('#'):
            continue
        values.pop(0)
        meta = dict(zip(fields, values))
        data.append(meta)
    return data


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


def is_processed_bin(desc, meta):
    ''' Putting bam files and select 20kb files into the processed file bin
        this is a specific check for those attributes
    '''
    if 'mapped reads' in desc:
        return True
    if desc.startswith('20kb bin'):
        if (meta.get('file_type') == 'normalized counts' and meta.get('file_format') == 'bw') or (
                meta.get('file_type') == 'LADs' and meta.get('file_format') == 'bed'):
            return True
    return False


def create_patch(item, label, rep=None):
    patch = {}
    if rep:
        label = label + ' ' + rep
    item_pfs = item.get('processed_files')
    item_opfs = item.get('other_processed_files')
    if not (item_pfs or item_opfs):
        print("NO FILES FOR {}".format(item.get('uuid')))
        return
    if item_pfs:
        patch['processed_files'] = item_pfs
    if item_opfs:
        for bin, opfs in item_opfs.items():
            if bin == 'Other':
                opftitle = 'Other files - non-binned'
                opfdesc = 'Non-bin specific files for {}'.format(label)
            elif bin == '20kb bin':
                opftitle = 'Additional {}ned files'.format(bin)
                opfdesc = 'Additional files associated with the {} size processing of data for {}'.format(bin, label)
            else:
                opftitle = '{}ned files'.format(bin)
                opfdesc = 'The files associated with the {} size processing of data for {}'.format(bin, label)
            patch.setdefault('other_processed_files', []).append(
                {'title': opftitle, 'description': opfdesc, 'type': 'supplementary', 'files': opfs})
    return patch


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

    repre = re.compile(r'_r\d+_')
    binre = re.compile(r'^\S+ bin')
    erepnore = re.compile(r'replicate\s\d+')

    # this if for parsing excel but could use fourfront query
    infile = args.input[0]
    query = None
    if len(args.input) > 1:
        query = args.input[1]

    metadata = extract_rows(infile)
    esets = {}
    # going row by row to add file to correct spot
    for meta in metadata:
        # checking if we have linked dataset info in sheet - should be either an
        # experiment set in this case or experiment (perhaps in the future)
        linked_set_id = meta.get('#linked datasets')
        file_alias = meta.get('aliases')

        # build basic ds for the set
        if linked_set_id not in esets:
            eset = get_metadata(linked_set_id, auth)
            euuid = eset.get('uuid')
            if not euuid:
                print("Can't get uuid for {} - skipping".format(linked_set_id))
                continue
            label = eset.get('dataset_label') + ' ' + eset.get('condition')
            esets[linked_set_id] = {'uuid': euuid, 'label': label, 'processed_files': [], 'other_processed_files': {}, 'experiments': {}}
            expts = eset.get('experiments_in_set')
            for expt in expts:
                exuid = expt.get('uuid')
                exmeta = get_metadata(exuid, auth)
                exdesc = exmeta.get('description')
                erepm = erepnore.search(exdesc)
                erep = 'replicate'
                if erepm:
                    erep = erepm.group()
                exalias = exmeta.get('aliases')[0] + '_'
                esets[linked_set_id]['experiments'][exalias] = {'uuid': exuid, 'erep': erep, 'processed_files': [], 'other_processed_files': {}}

        # use description to get replicate number if any and bin size if any
        desc = meta.get('description')

        bin = binre.match(desc)
        repno = repre.search(desc)
        if not repno:
            # file should get linked to the set
            if 'mapped reads' in desc:
                # it's a bam file so should be linked to an experiment
                print("Can't find replicate info for {}\t{}".format(file_alias, desc))
                continue
            # check if should be in pf bin
            if is_processed_bin(desc, meta):
                esets[linked_set_id]['processed_files'].append(file_alias)
            else:
                if bin:
                    bin = bin.group()
                else:
                    bin = 'Other'
                esets[linked_set_id]['other_processed_files'].setdefault(bin, []).append(file_alias)
            continue
        # if we're here means we have a replicate number so get it and find the right expt
        repno = repno.group()
        expts = esets[linked_set_id]['experiments'].keys()
        repexpt = None
        for exp in expts:
            if exp.endswith(repno):
                repexpt = esets[linked_set_id]['experiments'][exp]
                break
        if not repexpt:
            print("Can't find a replicate experiment for {} with {}".format(linked_set_id, repno))
            continue
        if is_processed_bin(desc, meta):
            repexpt['processed_files'].append(file_alias)
        else:
            if bin:
                bin = bin.group()
            else:
                bin = 'Other'
            repexpt['other_processed_files'].setdefault(bin, []).append(file_alias)

    # import pdb; pdb.set_trace()
    # create the patches assuming no existing files present
    patch_data = {}
    for eset in esets.values():
        label = eset.get('label')
        patch = create_patch(eset, label)
        if patch:
            patch_data[eset.get('uuid')] = patch

        expts = eset.get('experiments')
        for expt in expts.values():
            epatch = create_patch(expt, label, expt.get('erep'))
            if epatch:
                patch_data[expt.get('uuid')] = epatch

    if patch_data:
        for puuid, pdata in patch_data.items():
            print(puuid, '\n', pdata, '\n\n')
            if args.dbupdate:
                try:
                    res = patch_metadata(pdata, puuid, auth)
                    print(res.get('status'))
                except Exception:
                    print("Can't patch {iid} with\n\t{p}".format(iid=puuid, p=pdata))


if __name__ == '__main__':
    main()

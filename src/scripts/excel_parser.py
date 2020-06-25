#!/usr/bin/env python3
import sys
import argparse
import xlrd
import datetime
import re

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


if __name__ == '__main__':
    main()

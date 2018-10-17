# geo2fdn

This script is used to grab a GEO dataset series and export it to a 4DN metadata workbook.


### Command line usage

Example usage:

```console
python3 path/to/scripts/geo2fdn.py GSE102740 -i blank_submit4dn_workbook.xls -o output_workbook.xls \
[-e me@gmail.com -t HiC]
```

Parameters:

-i / --infile     &nbsp; : &nbsp;  input file - blank 4DN workbook to be filled (.xls file). \
-o / --outfile    &nbsp; : &nbsp;  output file


Optional:

-e / --email      &nbsp; : &nbsp;  email address - \
Use of NCBI Entrez requires an email address to be specified. If not specified,
there will be a prompt to input email address, but in this case console output
cannot be redirected to a log file.\
-t / --type       &nbsp; : &nbsp;  experiment type - \
This parameter can be use to force the experiment type of all experiments in the
given GEO series. If not specified, the script will attempt to parse experiment type
from experiment records. DO NOT specify if GEO series ßhas multiple experiment types.


### Installation

1. First clone the dcicwrangling repository:
    ```console
    git clone https://github.com/4dn-dcic/dcicwrangling.git
    ```
2. Install the required dependencies, preferably in a python3 virtual environment. I use python 3.6.
   ```console
   pip install -r requirements.txt
   ```

### Running

Run the script: \
`python3 path/to/scripts/geo2fdn.py GSEXXXXX -i <infile.xls> -o <outfile.xls> -e <email_address>`

Below is a basic outline of what happens when the script is run.
1. The GEOparse library is called, which downloads the SOFT family file for the GEO series
specified.
2. The experiment records for each experiment are parsed, and for each experiment record an
attempt to assign an experiment type is made if the `-t` option was not used. When all the
experiment records have been parsed, the SOFT family file will be deleted.
3. For each experiment record containing a link to an SRA accession, a request will be made
to SRA and it will attempt to parse additional information from the SRA record for the experiment.
4. If a BioSample accession is linked to the experiment record, a request will be made to the
BioSample db and the BioSample record will be parsed. A GET request will also be made to the
4DN data portal to get a list of 4DN organisms. After the organism is parsed from the Biosample
record, if the organism is determined to be a non-4DN model, this biosample and experiment will
not be written to file.
5. After all information is parsed, it will look for the relevant sheets in the input workbook
and begin writing the output file. Sheets the script can partially fill out include Biosample,
BiosampleCellCulture, FileFastq, ExperimentHiC, ExperimentSeq, ExperimentDamid, ExperimentRepliseq,
ExperimentCaptureC, and ExperimentChiapet. If an Experiment sheet is present but experiment
records of that type have not been parsed from the GEO series, a warning message will be printed
to the console. Conversely, if experiments of a particular experiment type parsed from the GEO
series do not have a corresponding sheet in the input file, a warning message will be printed
to the console.
6. When all the experiment sheets are finished writing, the output workbook will be saved and the
script will exit.

### Console output

Sample output:
```console
17-Oct-2018 10:34:05 INFO GEOparse - Downloading ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE102nnn/GSE102740/soft/GSE102740_family.soft.gz to ./GSE102740_family.soft.gz
17-Oct-2018 10:34:05 INFO utils - Downloading ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE102nnn/GSE102740/soft/GSE102740_family.soft.gz to ./GSE102740_family.soft.gz

17-Oct-2018 10:34:06 INFO GEOparse - Parsing ./GSE102740_family.soft.gz:
17-Oct-2018 10:34:06 DEBUG GEOparse - DATABASE: GeoMiame
17-Oct-2018 10:34:06 DEBUG GEOparse - SERIES: GSE102740
17-Oct-2018 10:34:06 DEBUG GEOparse - PLATFORM: GPL11154
17-Oct-2018 10:34:06 DEBUG GEOparse - SAMPLE: GSM2745839
17-Oct-2018 10:34:06 DEBUG GEOparse - SAMPLE: GSM2745840
17-Oct-2018 10:34:06 DEBUG GEOparse - SAMPLE: GSM2745841
17-Oct-2018 10:34:06 DEBUG GEOparse - SAMPLE: GSM2745842
17-Oct-2018 10:34:06 DEBUG GEOparse - SAMPLE: GSM2745843
GEO parsing done. Removing downloaded soft file.
Fetching BioSample record...
Fetching BioSample record...
Fetching BioSample record...
Fetching BioSample record...
Fetching BioSample record...
Writing Biosample sheet...
Writing BiosampleCellCulture sheet...
Writing FileFastq sheet...
Writing ExperimentHiC sheet...

No ChIP-seq, RNA-seq, SPRITE, or TSA-seq experiments parsed from GSE102740.
If all samples are known to be ChIP-seq, RNA-seq, SPRITE, or TSA-seq experiments,
this script can be rerun using -t <experiment_type>

Wrote file to GSE102740_metadata.xls.
```

#### GEOparse output

The first portion of script output will be the GEOparse output as it is downloading the SOFT format
family file and parsing it. Any errors at this stage may likely be due to a wrong GEO series accession,
or a defective SOFT family file. If stdout is redirected to a log file, this part will still print to
the console.

#### SRA errors

After parsing the GSM files, the script will attempt to send an SRA request for each GSM linked
to an SRA accession. If there is an SRA accession linked but the SRA record hasn't been publicly
released yet, an error message will indicate that. If there is a different error message about
the SRA record, it could indicate that the xml was malformed.

#### Biosample records

The next portion of the script's console output will be a series of lines that read
`Fetching Biosample record...`. The information about each sample in the NCBI BioSample
db is not part of the SOFT family file and must be requested separately.

#### Writing sheets

The next portion of the console output for a successful run will be a series of lines
mentioning the worksheets being written to, typically starting with `Writing Biosample sheet...`.
Only sheets present in the input workbook will be written, and only if the relevant information
has been found and parsed.

#### Warning messages

**Experiment sheets not written:** If there are Experiment sheets in the input workbook for
experiment types that are not present in the specified GEO series, there will be output
messages warning the user that these sheets were not written. If you expected these experiment
types to be absent from the GEO series, no action is needed. Otherwise, if you were expecting
one of these experiment types to be parsed from the series, it is possible that the script
was unable to parse the experiment type from the GEO series. If this is the case, and if all
experiments in the series are of the same experiment type, you can rerun the script using
the `-t <exptype>` option to force the experiment type. If there is more than one experiment
type in the GEO series, however, this will not work and the experiments with the unparsed
type(s) may have to be filled out in the workbook manually.

**Experiment records not written:** If an experiment type has been parsed from the GEO series
for which the corresponding Experiment sheet was not found in the input workbook, a
message will be printed to the console indicating that. If it's an experiment type you wish
to have present in the output workbook, then you can generate a new workbook with Submit4DN
that includes that particular Experiment sheet, and run the script again.

**Non-4DN organisms:** If any of the experiment records in the GEO series were from organisms
not in the 4DN data portal, a warning message will be printed and these experiments as well
as their corresponding fastq and biosample information won't be written to file. Current 4DN
organisms include human, mouse, fly, worm, and chicken. If more are added in the future the
script will work on those.

**Non-4DN experiment types:** If experiment types were parsed from the GEO series records
that aren't experiments currently carried on the portal, these won't be written to file.
Some of these include 4C-seq, GRO-seq, and Bisulfite-seq. A warning message will be printed
if any of these are included in the GEO series.

**Unparsable experiment types:** If the `-t` option was not used and some experiment records
had experiment types that could not be parsed, a warning message will be printed and these
won't be written to file. If all the experiments in the GEO series are the same unparsable
type, the script can be rerun with the `-t <exp_type>` option; if there are multiple
experiment types, then the script will not work and the workbook will need to be filled out
manually.

#### Final console output

The last line printed to console will read `Wrote file to <outfile.xls>`. If the console output
or log file does not end with this, then it means the script didn't finish running successfully.

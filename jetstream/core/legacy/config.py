"""
# Comments from original validation script:

### check if we can process this config or just hold it
### validate email address
### validate number of fastq lines > 0
### validate fastq files exist (R2 also)
### validate fastq read group exists
### validate project name
### validate results directory is present
### validate pipeline name is present
# Pipeline name is valid
### validate recipe name
# Recipe name is valid
### validate save recipe
# save recipe is valid
### validate debit account name
#validate sample is only defined once
#validate sample name does not contain a period
#validate kit code is 5 characters
#validate kit code for exomes for this sample is valid
### validate kit name, sample name
# validate RNA strandedness is known
# validate RNA has star index defined for this read length
#validate triplet line contains sample names that are valid

### check if genome samples exist
    ### if allele count is requested make sure first two is set up as a dna pair
    ### and make sure third variable is RNA
    # check  that CIRCOS variable is set
    # if circos is yes we have to make sure circos exome pair exists and theyre
    both exome
### validate if RNA sample exists TOPHATGTF, USEMASK vars are defined

### validate FQ= in Pegasus pipe formatted correctly

### Validate dnaPair samples exist
### Validate dnaFami samples exist
### Validate rnaPair samples exist
"""
import logging
from collections import OrderedDict

from jetstream.utils import Source

log = logging.getLogger(__name__)


class ConfigParsingException(Exception):
    """ Raised when config files contain syntax errors """


def load(path):
    """Reads a legacy config file from the given path, returns
    config object"""
    with open(path, 'r') as fp:
        return loads(fp.read())


# def dump(*args, **kwargs):
#     """ There is no dumper for legacy config files. You shouldn't be
#      converting to the old format """
#     raise NotImplementedError


def loads(data):
    """Generates a legacy config file from data. Performs several validation
    steps and adds some additional attributes. Briefly:

     - Leading and trailing whitespace is removed
     - Pipeline name is either 'medusa' or 'pegasus' (case insensitive)
     - Contains single occurrence of "=START" and "=END" lines
     - No data following "=END" line
     - All metadata keys are translated to lower-case
     - "Kit" given in a SAMPLE line is also added to each data object for
       that sample
     - "Assay" value given in a SAMPLE line is also added to each data object
       for that sample

    """
    source = Source(data.strip())

    # Parse meta lines
    meta_lines, sample_lines = _split_sections(source)
    meta = _parse_meta_lines(meta_lines)

    which_pipeline = meta['pipeline'].casefold()
    if which_pipeline not in ('pegasus', 'medusa'):
        raise ConfigParsingException('Unknown pipeline: {}'.format(meta['pipeline']))

    # Parse sample lines
    sample_line_groups = _group_sample_lines(sample_lines)
    samples = []
    for group in sample_line_groups:
        try:
            s = _parse_sample(group)
            samples.append(s)
        except Exception as err:
            msg = '{} while parsing group:\n{}'.format(err, '\n'.join(group))
            raise ConfigParsingException(msg)

    samples = [_parse_sample(group) for group in sample_line_groups]
    samples = _add_extra_data(samples)

    return {'meta': meta, 'samples': samples}


def _split_sections(source):
    """ Split the metadata lines from the sample lines """
    lines = [line for line in source.splitlines() if line]

    start_line = '=START'
    end_line = '=END'

    # Check that start_str exists once and only once
    if lines.count(start_line) != 1:
        raise ConfigParsingException('No "=START" line found!')
    else:
        start = lines.index('=START')

    # Check that end_str exists once and only once
    if lines.count(end_line) != 1:
        raise ConfigParsingException('No "=END" line found!')
    else:
        end = lines.index('=END')

    # Check that nothing is present after end line
    if lines[-1] != "=END":
        raise ConfigParsingException('Lines found after "=END"')

    # Now split the lines into two groups, meta and sample
    meta = lines[0: start]
    sample = lines[start + 1: end]
    return meta, sample


def _parse_meta_lines(lines):
    """ Each line in metadata should follow a "key=value" syntax. This
    function splits the lines in metadata into key-value pairs and
    returns an OrderedDict of the metadata.

    Note: This ignores case on the keys and all keys in the resulting
    dict will be converted to lower-case.

    """
    kv_tuples = []
    for line in lines:
        try:
            key, value = line.split('=')
            key = key.lower()
            kv_tuples.append((key, value))
        except ValueError:
            msg = 'Error parsing metadata: "{}"'.format(line.print_ln())
            raise ConfigParsingException(msg) from None
    meta = OrderedDict(kv_tuples)
    return meta


def _group_sample_lines(lines):
    """ Groups sample lines together with data lines """
    samples = []

    sample_iter = iter(lines)
    line = next(sample_iter)

    if line.startswith('SAMPLE='):
        current_group = [line]
    else:
        raise ConfigParsingException('Sample lines should start with SAMPLE')

    while 1:
        try:
            line = next(sample_iter)
        except StopIteration:
            if current_group:
                samples.append(current_group)
            break

        if line.startswith('SAMPLE='):
            samples.append(current_group)
            current_group = [line]
        else:
            current_group.append(line)

    return samples


# The following functions convert the sample lines in a config file into
# sample and data objects (nested dictionary/list structure). This causes
# a couple small changes in the structure:
#
#    1) Data objects will inherit 'kit' and 'assay' properties from their SAMPLE
#
#    The kit code and assay are associated with a sample in the config files.
#    But, the assay is not really a property of the sample itself, it's a
#    property of the data object. For instance, one sample can be prepped
#    multiple times with different kits. Here, kit is copied as a property of
#    each data object.
#
#
#    2) Samples SOMETIMES have a library property, and data will ALWAYS have a
#    library property.
#
#    Dilution ID is part of the sample data for Medusa config files. This
#    was later changed in Pegasus. The dilution ID is also called a library,
#    and is eventually used for making read groups. This parser always adds
#    dilution id (library) as a property of the data. But, it also keeps
#    the dilution id as a sample property if given a medusa config file.
#

def _parse_sample(lines):
    """Create a structured sample from a list of sample lines"""
    sample_line = lines[0]
    s = {'data': [], 'line_number': sample_line.line_number}

    # The fields are everything after 'SAMPLE='
    fields = sample_line.partition('SAMPLE=')[2]

    try:
        # Pegasus
        s['kit'], s['name'], s['assay'], s['library'] = fields.split(',')
    except ValueError:
        # Medusa
        s['kit'], s['name'], s['assay'] = fields.split(',')


    for line in lines[1:]:
        d = {'line_number': line.line_number}
        d['type'], _, data_fields = line.partition('=')  # ex: "FQ=..."
        d['rg_id'], d['path'] = data_fields.split(',')

        try:
            # Pegasus
            d['fcid'], d['lane'], d['library'] = d['rg_id'].split('_')
        except ValueError:
            # Medusa
            d['fcid'], _, d['lane'] = d['rg_id'].partition('_')
            d['library'] = s['library']

        s['data'].append(d)

    return s


def _add_extra_data(samples):
    """Copies some data from the sample properties to all of its data
    objects. Also generates read group data. Note this follows the TGen
    convention of PU: FCID_LANE and ID:FCID_LANE[_LIBRARY] where LIBRARY
    may not be present in all RG:ID tags. This is generally unimportant
    unless you are considering merging SAMs. """
    for sample in samples:
        for data in sample['data']:
            data['kit'] = sample['kit']
            data['assay'] = sample['assay']

            if data['type'] == 'FQ':
                data['read_style'] = 'paired-end'

            data['read_group'] = {
                'ID': data['rg_id'],
                'CN': 'TGen',
                'LB': data['library'],
                'PL': 'ILLUMINA',
                'PU': '{}_{}'.format(data['fcid'], data['lane']),
                'SM': sample['name']
            }

    return samples
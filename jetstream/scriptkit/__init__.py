from jetstream.scriptkit.batch_schedulers import slurm
from jetstream.scriptkit import formats
from jetstream.scriptkit.formats.refdict import parse_refdict_line


def read_group(*, ID=None, CN=None, DS=None, DT=None, FO=None, KS=None,
               LB=None, PG=None, PI=None, PL=None, PM=None, PU=None,
               SM=None, strict=True, **unknown):
    """Returns a SAM group header line. This function takes a set of keyword
    arguments that are known tags listed in the SAM specification:

        https://samtools.github.io/hts-specs/

    Unknown tags will raise a TypeError unless 'strict' is False

    :param strict: Raise error for unknown read group tags
    :return: Read group string
    """
    if unknown and strict:
        raise TypeError('Unknown read group tags: {}'.format(unknown))

    fields = locals()
    col_order = ('ID', 'CN', 'DS', 'DT', 'FO', 'KS', 'LB', 'PG', 'PI', 'PL',
                 'PM', 'PU', 'SM')

    final = ['@RG']
    for field in col_order:
        value = fields.get(field)
        if value is not None:
            final.append('{}:{}'.format(field, value))

    return '\t'.join(final)


# def cna_index_template(refdict):
#     with open(refdict, 'r') as fp:
#         lines = fp.readlines()
#
#     seqs_to_print = {i: None for i in range(1, 25)}
#
#     for l in lines:
#         groups = parse_refdict_line(l)
#
#         if groups is None:
#             continue
#
#     lines = [parse_refdict_line(l) for l in lines]

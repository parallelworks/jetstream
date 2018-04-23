import os
import traceback
import logging
import jetstream

log = logging.getLogger(__name__)
RUN_DATA_DIR = '.jetstream'

# TODO: should project functions walk up the directory tree like git?
# see this https://gist.github.com/zdavkeos/1098474 but also consider
# this:
# [rrichholt@dback-login1:~]$ git pull
# fatal: Not a git repository (or any parent up to mount point /home)
# Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).


class ProjectDataNotFound(Exception):
    """Raised when a reference to project data is made for a
    file that does not exist. """
    pass


class NotAProject(Exception):
    pass


class NotARun(Exception):
    pass


class Project:
    """Internal representation of a project. A project is a directory
    with a run data dir ('project/.jetstream'). Additionally there are
    some data files describing the contents and settings of the project.
    This object provides an interface for easy access to project info.

    Here is a description of the data files that can be present in a
    project their associated getter methods:

    Project.samples() will return a list of all sample records in the project
    data with their associated data records in an list accessible with
    sample['data']. Note that if sample definitions are included in
    project.data['samples'], they will be joined with the samples_names in
    data records.

    Project.samples(key=value) returns list of sample records in the that has
    been filtered based on the key/value requirements

    """
    def __init__(self, path=None):
        self.path = path or os.getcwd()
        self.name = os.path.basename(self.path)
        self.config = dict()
        self._run_id = ''
        self._run_path = ''

        if not os.path.exists(self.path):
            raise NotAProject('Path does not exist: {}'.format(self.path))

        if not os.path.isdir(self.path):
            raise NotAProject('Not a directory: {}'.format(self.path))

        target = os.path.join(self.path, RUN_DATA_DIR)
        if not os.path.exists(target):
            raise NotAProject('Data dir does not exist {}'.format(target))

        target = os.path.join(self.path, RUN_DATA_DIR)
        if not os.path.isdir(target):
            raise NotAProject('Data dir is not a dir {}'.format(target))

        self._load_project_config_files()
        log.critical('Loaded project {}'.format(self.path))

    def _load_project_config_files(self):
        """Loads all data files in the project/config as values in the
        project.config dictionary.

        Legacy configs are handled differently than other data files. If the
        name of the config file matches the name of the project, the values
        for "meta" and "data" are added directly to project.data and will
        overwrite any previous values. Legacy config files with names other
        than the current project name are handled just like other data files.
        """
        # TODO Smarter merging of config files when some records can
        # be stored in multiple files https://pypi.org/project/jsonmerge/
        config = dict()
        project_legacy_config = None
        for path in loadable_files(self.path):
            name = name_a_path(path)

            if path.endswith('.config') and name == self.name:
                # Handle legacy configs, see docstring
                project_legacy_config = path
                continue

            try:
                config[name] = load_data_file(path)
            except Exception as e:
                log.warning('Unable to parse project config {}'.format(path))
                log.debug(traceback.format_exc())

        if project_legacy_config is not None:
            parsed = load_data_file(project_legacy_config)
            config.update(parsed)

        self.config = config

    def serialize(self):
        """Returns a dictionary of all data available for this project"""
        return vars(self)

    def runs(self):
        """Find all run folders for this project"""
        runs = []
        run_data_dir = os.path.join(self.path, RUN_DATA_DIR)
        for i in os.listdir(run_data_dir):
            p = os.path.join(run_data_dir, i)
            if os.path.isdir(p):
                runs.append(i)
        return runs

    def latest_run(self):
        try:
            latest = sorted(self.runs())[-1]
            return latest
        except IndexError:
            return None

    def list_samples(self, **kwargs):
        """ Returns a list of all sample records in project.config. This is
        ephemeral project data generated by joining records from several
        project config files (if they are present):

        - Starting with any records in under project.config["samples"]
        - Joining those records with any found under project.config["data"]
          key if they match on the "sample_name" property.
        - Filtering the results by any given kwargs

        """
        project_data = self.config

        # Find all samples in self.config['samples']
        if 'samples' in project_data:
            samples = {s['sample_name']: s for s in project_data['samples']}
        else:
            samples = {}

        # Sort all data objects from project.config['data'] into samples
        if 'data' in project_data:
            for record in project_data['data']:
                name = record['sample_name']
                if not name in samples:
                    samples[name] = {
                        'sample_name': name,
                        'data': []
                    }

                samples[name]['data'].append(record)

        # Turn it into a list so we can filter based on kwargs
        sample_list = list(samples.values())

        if kwargs:
            return jetstream.utils.filter_documents(sample_list, kwargs)
        else:
            return sample_list


def init():
    if os.path.exists('.jetstream/created'):
        log.critical('{} is already a project.'.format(os.getcwd()))
    else:
        os.makedirs('.jetstream', exist_ok=True)
        with open('.jetstream/created', 'w') as fp:
            fp.write(jetstream.utils.yaml_dumps(jetstream.utils.fingerprint()))
        log.critical('Initialized project {}'.format(os.getcwd()))


data_loaders = {
    '.txt': jetstream.utils.table_to_records,
    '.csv': jetstream.utils.table_to_records,
    '.mer': jetstream.utils.table_to_records,
    '.tsv': jetstream.utils.table_to_records,
    '.json': jetstream.utils.json_load,
    '.yaml': jetstream.utils.yaml_load,
    '.yml': jetstream.utils.yaml_load,
    '.config': jetstream.legacy.config.load,
}


def loadable_files(path):
    """Generator yields all files we can load (see data_loaders) """
    for file in os.listdir(path):
        if os.path.isfile(file) \
                and file.endswith(tuple(data_loaders.keys())):
            yield os.path.join(path, file)


def name_a_path(path):
    """ Names a path by removing its directories and extension """
    # TODO this might need some more rules in the future
    return os.path.splitext(os.path.basename(path))[0]


def load_data_file(path):
    """Attempts to load a data file from path, raises Value error
    if an suitable loader function is not found in data_loaders"""
    for ext, fn in data_loaders.items():
        if path.endswith(ext):
            loader = fn
            break
    else:
        raise ValueError('No loader fn found for {}'.format(path))

    log.debug('Loading {} with {}.{}'.format(
        path, loader.__module__, loader.__name__))

    return loader(path)

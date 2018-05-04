import os
import traceback
import logging
import jetstream

log = logging.getLogger(__name__)
RUN_DATA_DIR = '.jetstream'


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
        self.config_path = os.path.join(self.path, 'config')
        self.temp_path = os.path.join(self.path, 'temp')
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
        log.critical('Loaded project: {}'.format(self.path))

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
        for path in loadable_files(self.config_path):
            name = name_a_path(path)

            # Handle legacy configs, see docstring
            if path.endswith('.config') and name == self.name:
                project_legacy_config = path
                continue

            try:
                config[name] = load_data_file(path)
            except Exception:
                log.warning('Unable to parse project config: {}'.format(path))
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

    def samples(self):
        """Build a dictionary of all sample records in project.config.
       This is ephemeral project data generated by joining records from several
       project config files (if they are present):

       - Starting with any records in under project.config["samples"]
       - Joining those records with any found under project.config["data"]
         key if they match on the "sample_name" property.
       - Filtering the results by any given kwargs

       """
        if 'samples' in self.config:
            samples = {s['sample_name']: s for s in self.config['samples']}
        else:
            samples = {}

        # Sort all data objects from project.config['data'] into samples
        if 'data' in self.config:
            for record in self.config['data']:
                record_sample_name = record['sample_name']

                if record_sample_name not in samples:
                    samples[record_sample_name] = {
                        'sample_name': record_sample_name,
                        'data': []
                    }

                if 'data' not in samples[record_sample_name]:
                    samples[record_sample_name]['data'] = []

                samples[record_sample_name]['data'].append(record)

        return samples

    def list_samples(self, **kwargs):
        """Returns a (filtered) list of all sample records in project.config.

        This list contains the values of all records found by Project.samples.
        It will be filtered to contain only records where attributes match the
        given kwargs. """
        sample_list = list(self.samples().values())

        if kwargs:
            return jetstream.utils.filter_records(sample_list, kwargs)
        else:
            return sample_list


def init(path=None):
    cwd = os.getcwd()
    try:
        if path is not None:
            os.makedirs(path, exist_ok=True)
            os.chdir(path)

        os.makedirs('.jetstream', exist_ok=True)
        os.makedirs('config', exist_ok=True)
        os.makedirs('temp', exist_ok=True)

        created_path = os.path.join('.jetstream', 'created')
        if not os.path.exists(created_path):
            with open(created_path, 'w') as fp:
                created = jetstream.utils.fingerprint()
                jetstream.utils.yaml.dump(created, stream=fp)
            log.critical('Initialized project: {}'.format(os.getcwd()))
        else:
            log.critical('Reinitialized project: {}'.format(os.getcwd()))

    finally:
        os.chdir(cwd)


def loadable_files(directory):
    """Generator yields all files we can load (see data_loaders) """
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        if os.path.isfile(path) \
                and path.endswith(tuple(data_loaders.keys())):
            yield path


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

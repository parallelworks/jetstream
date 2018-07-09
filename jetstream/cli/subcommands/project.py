"""Interact with jetstream projects."""
import sys
import argparse
import logging
import jetstream

log = logging.getLogger(__name__)


def arg_parser(actions=None):
    parser = argparse.ArgumentParser(
        prog='jetstream project',
        description=__doc__
    )

    parser.add_argument('action', choices=actions,
                        help='action name')

    parser.add_argument('args', nargs=argparse.REMAINDER,
                        help='remaining args are passed to the chosen action')

    return parser


def init_arg_parser():
    """Argument parser for the init action"""
    parser = argparse.ArgumentParser(
        prog='jetstream project init',
        description='Initialize a Jetstream project'

    )

    parser.add_argument('path', nargs='?', default='.',
                        help='Path to a Jetstream project')

    return parser


def config_arg_parser():
    """Argument parser for the config action"""
    parser = argparse.ArgumentParser(
        prog='jetstream project config',
        description='Summarize project configuration data'
    )

    parser.add_argument('path', nargs='?', default='.',
                        help='Path to a Jetstream project')

    parser.add_argument('--format', choices=['yaml', 'json'], default='json')

    parser.add_argument('--json', dest='format',
                        action='store_const', const='json',
                        help='Output JSON')

    parser.add_argument('--yaml', dest='format',
                        action='store_const', const='yaml',
                        help='Output YAML')

    parser.add_argument('--pretty', action='store_true', default=False,
                        help='Human-friendlier output')

    return parser


def samples_arg_parser():
    parser = config_arg_parser()
    parser.prog = 'jetstream project samples'
    parser.description = 'List samples in a project'

    return parser


def tasks_arg_parser():
    """Argument parser for the data action"""
    parser = argparse.ArgumentParser(
        prog='jetstream project tasks',
        description='Summarize project tasks. If `task_id` is not given, all '
                    'task ids will be listed.'
    )

    parser.add_argument('task_id', nargs='*',
                        help='Task ID to summarize')

    parser.add_argument('--path', default='.',
                        help='Jetstream project path')

    return parser


def runs_arg_parser():
    parser = argparse.ArgumentParser(
        prog='jetstream project runs',
        description='Records are saved for every workflow that has been run on'
                    'a project. This command lists the run ids in a project.'
    )

    parser.add_argument('path', nargs='?', default='.',
                        help='Path to a Jetstream project')

    return parser


def init(args=None):
    parser = init_arg_parser()
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))

    jetstream.projects.init(args.path)


def config(args=None):
    parser =config_arg_parser()
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))

    p = jetstream.Project(args.path)

    if args.format == 'json':
        if args.pretty:
            print(jetstream.utils.json.dumps(p.config, indent=4))
        else:
            print(jetstream.utils.json.dumps(p.config))
    elif args.format == 'yaml':
        jetstream.utils.yaml.dump(p.config, stream=sys.stdout)


def samples(args=None):
    parser = config_arg_parser()
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))

    p = jetstream.Project(args.path)

    if args.format == 'json':
        if args.pretty:
            print(jetstream.utils.json.dumps(p.samples(), indent=4))
        else:
            print(jetstream.utils.json.dumps(p.samples()))
    elif args.format == 'yaml':
        jetstream.utils.yaml.dump(p.samples(), stream=sys.stdout)


def tasks(args=None):
    parser = tasks_arg_parser()
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))

    p = jetstream.Project(args.path)
    wf = p.load_workflow()
    tasks = {t.id: t for t in wf.tasks(objs=True)}

    if args.task_id:
        for task_id in args.task_id:
            print(tasks[task_id].pretty())
    else:
        for t in tasks.values():
            print(t)


def runs(args=None):
    parser = runs_arg_parser()
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))

    p = jetstream.Project(args.path)

    for r in p.runs():
       print(r.id, r.info.get('datetime'))


def main(args=None):
    actions = {
        'init': init,
        'config': config,
        'samples': samples,
        'tasks': tasks,
        'runs': runs,

    }

    parser = arg_parser(actions=list(actions.keys()))
    args = parser.parse_args(args)
    log.debug('{}: {}'.format(__name__, args))
    actions[args.action](args.args)

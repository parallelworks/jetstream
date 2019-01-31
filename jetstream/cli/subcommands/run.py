"""Run Jetstream from a template, module, or workflow

Template Variable Data:

To render the template, a config object will be generated by loading
variables from the current project (when working inside a project) and command
args. The priority order for template variables is as follows:

1) Config variables given by command arguments: ``--<type>:<key> <value>``
2) Current project config file: ``<project>/jetstream/config.yaml``


Detailed argument help:

--mode

    This option controls how the workflow will be loaded

    - template (default): build and run a workflow from a template
    - module: build and run a workflow from a Python module
    - workflow: load and run a pre-built workflow


--reset-method

    This option controls which tasks will be reset when the runner starts

    - retry (default): all pending and failed tasks will be reset
    - resume: all pending tasks will be reset
    - reset: all tasks will be reset

"""
import logging
import jetstream
from jetstream import settings
from jetstream.templates import context, render_template

log = logging.getLogger(__name__)


def arg_parser(parser):
    parser.add_argument(
        'path',
        help='Path to a workflow template, python module, or workflow file'
    )

    parser.add_argument(
        '--backend',
        help='Specify the runner backend used for executing tasks'
    )

    parser.add_argument(
        '--build-only',
        action='store_true',
        help='Just render the template, build the workflow, and stop. This '
             'can be used to validate a template and data prior to running.'
    )

    parser.add_argument(
        '--mode',
        choices=['template', 'module', 'workflow'],
        default='template',
        help='Run modes, see the descriptions below.'
    )

    parser.add_argument(
        '-o', '--out',
        default=None,
        help='Path to save the workflow file after it is built. Only used'
             'if running with "--build-only"'
    )

    parser.add_argument(
        '--run-id',
        help='Give this run a specific ID instead of randomly generating one.'
    )

    parser.add_argument(
        '--reset-method',
        choices=['retry', 'resume', 'reset'],
        default=None,
        help='Method to use when running existing workflows. This parameter '
             'will determine which tasks are reset prior to starting the run.'
    )

    parser.add_argument(
        '--workflow-format',
        choices=['yaml', 'json', 'pickle'],
        help='Set the workflow file format instead of guessing from the file '
             'extension.'
    )

    return parser


def main(args):
    log.debug(f'{__name__} {args}')

    # Get the runner setup first so that we find errors here before spending
    # time building the workflow
    cls, params = jetstream.lookup_backend(args.backend)
    runner = jetstream.Runner(cls, params)

    # Setup the workflow, this can be built from a template, python module, or
    # loaded from a file.
    if args.mode == 'template':
        c = context(
            constants=settings['constants'].get(dict),
            project=args.project,
            command_args=args.kvargs
        )
        workflow = render_template(args.path, c)
    elif args.mode == 'module':
        raise NotImplementedError
    else:
        workflow = jetstream.load_workflow(args.path, args.workflow_format)

    if args.project:
        try:
            existing_wf = args.project.workflow
            workflow = jetstream.workflows.mash(existing_wf, workflow)
        except FileNotFoundError:
            pass

    if args.build_only:
        if args.out:
            workflow.save(args.out)
        return

    # Resetting tasks allows workflows that were stopped prior to completion to
    # be rerun. Or tasks that failed due to external state can be retried.
    if args.reset_method == 'retry':
        workflow.retry()
    elif args.reset_method == 'resume':
        workflow.resume()
    elif args.reset_method == 'reset':
        workflow.reset()
    elif args.reset_method is None:
        pass
    else:
        raise ValueError(f'Unrecognized task reset method: {args.reset_method}')


    runner.start(workflow, run_id=args.run_id, project=args.project)


if __name__ == '__main__':
    main()

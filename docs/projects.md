# Projects

Jetstream encourages project-oriented workflows. With this pattern, work is 
divided into separate directories (projects), and pipelines are executed on
specific projects. Projects are directories where a pipeline run will execute
and output files will be saved. Using projects makes it easier to organize logs
and run metadata. It also allows for incremental changes in a pipeline to be
applied without re-running the entire workflow.

Projects can be created with the `init` subcommand:

```
$ jetstream init <path to project>
```

This command will create a new directory and establish the index files. If the 
given directory already exists, the index files will be created in that 
directory.

Now, the `jetstream run` and `jetstream pipelines` commands will save run
progress, organize logs, and set the working directory for tasks. Using either
command while your current working directory is a project will automatically set
the project option. Alternatively, specify the a project to use manually with
the  `--project` option. 

Projects are optional, here are some example features that are improved when
using projects:

| Feature      | with projects      | without project                         |
|--------------|--------------------|-----------------------------------------|
| Run Progress | Saved in project   | Saved only if -o/--outpath given        |
| Run Logs     | Saved in project   | Printed to stdout with LocalBackend or varies by backend |
| History      | Saved in project   | Not available                           |


## Project environment variables

When running workflows with a project, the following environmnet variable will be 
exported:

- `JS_PROJECT_PATH`: The path to the current project

## Project progress

When running workflows with a project, progress will be saved automatically in
`<project root>/jetstream/workflow.pickle`. When running new pipelines or 
templates in the project, the tasks are compared against the existing record and
only executed if they are: 

  - new tasks that were are not found in the project workflow file
  - are already in the workflow file, but have a 'failed' status
  - are already in the workflow file, but have changed (different [identity](tasks.md#identity))
  
 Note that the task name is used to make these comparisons. If a task name 
 changes during updates to a template, it will be considered a new task.
 

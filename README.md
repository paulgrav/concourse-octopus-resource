![Image Build](https://github.com/paulgrav/concourse-octopus-deployment/actions/workflows/image-push.yml/badge.svg?branch=main)

# Octopus Resource

Used to run tasks after successful Octopus deployments. Use cases include run functional tests, security tests, or smoke tests.

## Source Configuration

* `octopus_server_uri`: _Required_ URI of the Octopus server.

* `api_key`: _Required_ API Key used to authentication with the Octopus Server.

* `project_id`: _Required_ The project ID against which deployment events will be tracked.

* `debug`: _Optional_ `true` or `false` Used to output debug messages.


## Behavior

### `check`:

Produces new versions for all successful deployments in the specified project_id.

A version is represented by the DeploymentID

### `in`:

Deployment state is written to the filesystem, this includes variable data.

Note that variable names are sanitised:

- `[` is replaced with `.`
- `]` is removed
- ` ` is replaced with `_`

e.g., `Octopus.Action.Package[package-ref].PackageId` becomes `Octopus.Action.Package.package-ref.PackageId`

Variables can be subsequently loaded via a `load_var` step e.g.,

```
- load_var: octopus-vars
  file: octopus-project/variables.json
```

N.B.

Secret variables are not available.

Octopus variables that reference other variables are not expanded.


#### Files created by the resource

* `./deployment.json `: Contains the response from the Octopus’ deployment API

* `./variables.json `: A file containing a boolean for if the resource was run with elevated privileges.

### `out`:

Attaches any artifacts to the deployment.

Options are specified in the params.

* `artifact_path`: _Required_ The path of the artifact to be uploaded.

* `path`: _Required_ This must be the same as the resource name.

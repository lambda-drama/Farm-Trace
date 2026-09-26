### Farm Trace

[![CI](https://github.com/lambda-drama/Farm-Trace/actions/workflows/ci.yml/badge.svg)](https://github.com/lambda-drama/Farm-Trace/actions/workflows/ci.yml)

Farm Trace

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app farmtrace
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/farmtrace
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### Tests

```bash
bench --site <your-site> run-tests --app farmtrace
```

CI runs this on a site with **only frappe and farmtrace** installed (see `.github/workflows/ci.yml`).

Before any test runs, frappe preloads global test records by walking the doctypes that have a test
module and following **every Link field they contain, including the Link fields of their child
tables**. If a doctype in that walk belongs to an app that is not installed, frappe aborts the whole
run with `DoesNotExistError: DocType <name> not found`, so no test ever executes.

Some farmtrace Link fields point at doctypes from other apps (`Item`, `UOM`, `Supplier`, `Branch`,
`Warehouse`, `Main Certification`). A frappe-only site does not have those, so each doctype that
links to them prunes those branches from its test module with `IGNORE_TEST_RECORD_DEPENDENCIES`:

| Test module | Prunes |
| --- | --- |
| `crop/test_crop.py` | `Item` |
| `farm/test_farm.py` | `Main Certification` |
| `farm_purchase_intake/test_farm_purchase_intake.py` | `Item`, `UOM` |
| `farmer/test_farmer.py` | `Supplier` |
| `topic_category/test_topic_category.py` | `Branch` |
| `training_status/test_training_status.py` | `Branch`, `Warehouse` |
| `farmer_training/test_farmer_training.py` | `Branch` |

Worth knowing:

- The list only stops the walk, the doctype itself is still preloaded; that is harmless because a
  doctype without a `test_records.json` inserts nothing.
- Child tables are walked too, so pruning `Item` on `Farm Purchase Intake` also covers the
  `farm_purchase_intake_item.item` Link.
- Pruning is per test module, so a target reachable from several doctypes must be listed in each of
  their modules (`Branch` is listed three times).
- A doctype that is only reached through a Link (e.g. `Farmer Training`, reached from
  `Training Status`) still needs a test module of its own, otherwise nothing prunes its Links.
- Other apps on the site add their own Links (custom fields included), so a site that has extra apps
  installed can still abort the walk somewhere else; run tests on a clean site when in doubt.

So when you add a Link to a doctype from another app, either install that app on the test site (and
in `ci.yml`) or add the target to `IGNORE_TEST_RECORD_DEPENDENCIES` in the linking doctype's test
module. A test that needs real records for such a target requires installing the app.

### License

agpl-3.0


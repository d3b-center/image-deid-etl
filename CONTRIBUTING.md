# How to Contribute

- [Submitting Changes](#submitting-changes)

## Submitting Changes

We follow the git-flow development methodology. At a high level, we work on features in individual "feature branches" based on the `develop` branch. Then, when it's time to cut a release, we merge `develop` back into `master`.

See ["Using git-flow to automate your git branching workflow"](https://jeffkreeftmeijer.com/git-flow/) for a great introduction.

And, consider [installing](https://github.com/petervanderdoes/gitflow-avh/wiki/Installation) the git-flow extension to Git.

- **Step One:** Create a feature branch, based on `develop`:

  **With the git-flow extension:**

  ```console
  $ git flow feature start myinitials/myfeature
  ```

  **With vanilla Git:**

  ```console
  $ git checkout -b feature/myinitials/myfeature develop
  ```

- **Step Two:** Publish your branch to GitHub:

  **With the git-flow extension:**

  ```console
  $ git flow feature publish
  ```

  **With vanilla Git:**

  ```console
  $ git push -u origin feature/myinitials/myfeature
  ```

- **Step Three:** When you are ready to submit your changes, open a pull request against `develop`.

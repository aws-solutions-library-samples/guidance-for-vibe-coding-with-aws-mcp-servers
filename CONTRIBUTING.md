# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.

## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check [existing open](https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers/issues), or [recently closed](https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers/issues?utf8=%E2%9C%93&q=is%3Aissue%20is%3Aclosed%20), issues to make sure somebody else hasn't already reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

- A reproducible test case or series of steps
- The version of our code being used
- Any modifications you've made relevant to the bug
- Anything unusual about your environment or deployment

## Contributing via Pull Requests

### Pull Request Checklist

- [ ] Testing
  - Unit test added (prefer not to modify an existing test, otherwise, it's probably a breaking change)
  - Integration test added (if adding a new pattern or making a significant update to an existing pattern)
- [ ] Docs
  - **README**: README and/or documentation topic updated
  - **Design**: For significant features, design document added to `design` folder
- [ ] Title and Description
  - **Change type**: title prefixed with **fix**, **feat** or **chore** and module name in parenthesis, which will appear in changelog
  - **Title**: use lower-case and doesn't end with a period
  - **Breaking?**: last paragraph: "BREAKING CHANGE: <describe what changed + link for details>"
  - **Issues**: Indicate issues fixed via: "**Fixes #xxx**" or "**Closes #xxx**"

---

### Step 1: Open Issue

If there isn't one already, open an issue describing what you intend to contribute. It's useful to communicate in advance, because sometimes, someone is already working in this space, so maybe it's worth collaborating with them instead of duplicating the efforts.

### Step 2: Design

In your design proposal, describe the feature, its use case, and implementation approach. Include any architectural diagrams or interface definitions that help explain your proposal.

Once the design is finalized, you can re-purpose this PR for the implementation, or open a new PR to that end.

Good contributions should:

1. Be applicable to common use cases and easily reusable
2. Follow AWS Well-Architected principles (secure, reliable, scalable, cost-efficient)
3. Simplify complex configurations while maintaining security by default
4. Provide clear interfaces and integrate well with existing AWS services

### Step 3: Work your Magic

Now it's time to work your magic. Here are some guidelines:

- Coding style (abbreviated):
  - In general, follow the style of the code around you. The linter will run on every PR and modify files.
- Every change requires a unit test
- If you change APIs, make sure to update the module's README file
- Try to maintain a single feature/bugfix per pull request. It's okay to introduce a little bit of housekeeping
  changes along the way, but try to avoid conflating multiple features. Eventually all these are going to go into a
  single commit, so you can use that to frame your scope.
- For new features, review existing code in the `packages/` directory for patterns and conventions

#### Integration Tests

If you are working on a new feature that is using previously unused CloudFormation resource types, or involves
configuring resource types across services, you need to write integration tests that use these resource types or
features.

To the extent possible, include a section (like below) in the integration test file that specifies how the successfully
deployed stack can be verified for correctness. Correctness here implies that the resources have been set up correctly.
The steps here are usually AWS CLI commands but they need not be.

```ts
/*
 * Stack verification steps:
 * * <step-1>
 * * <step-2>
 */
```

### Step 4: Commit

Create a commit with the proposed changes:

- Commit title and message (and PR title and description) must adhere to [Conventional Commits](https://www.conventionalcommits.org).

  - The title must begin with `feat(module): title`, `fix(module): title` or `chore(module): title`.
  - Title should be lowercase.
  - No period at the end of the title.

- Commit message should describe _motivation_. Think about your code reviewers and what information they need in
  order to understand what you did. If it's a big commit (hopefully not), try to provide some good entry points so
  it will be easier to follow.

- Commit message should indicate which issues are fixed: `fixes #<issue>` or `closes #<issue>`.

- Shout out to collaborators.

- If not obvious (i.e. from unit tests), describe how you verified that your change works.

- If this commit includes breaking changes, they must be listed at the end in the following format (notice how multiple breaking changes should be formatted):

```
BREAKING CHANGE: Description of what broke and how to achieve this behavior now
* **module-name:** Another breaking change
* **module-name:** Yet another breaking change
```

### Step 5: Pull Request

- Push to a GitHub fork
- Submit a Pull Requests on GitHub.
- Please follow the PR checklist written above. We trust our contributors to self-check, and this helps that process!
- Discuss review comments and iterate until you get at least one “Approve”. When iterating, push new commits to the
  same branch. Usually all these are going to be squashed when you merge to main. The commit messages should be hints
  for you when you finalize your merge commit message.
- Make sure to update the PR title/description if things change. The PR title/description are going to be used as the
  commit title/message and will appear in the CHANGELOG, so maintain them all the way throughout the process.
- Make sure your PR builds successfully (we have GitHub actions setup to automatically build all PRs)

#### Build Process

- Pull requests are automatically checked for formatting and linting
- Local git hooks (via husky) run formatting and linting before each commit
- Run `pnpm format` and `pnpm lint` to format and lint code manually

### Step 6: Merge

- Once approved and tested, a maintainer will squash-merge to main and will use your PR title/description as the commit message.

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).

## Code of Conduct

This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
opensource-codeofconduct@amazon.com with any additional questions or comments.

## Security issue notifications

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.

## Licensing

See the [LICENSE](https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers/blob/main/LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.

We may ask you to sign a [Contributor License Agreement (CLA)](http://en.wikipedia.org/wiki/Contributor_License_Agreement) for larger changes.

---

&copy; Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

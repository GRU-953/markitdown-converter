# Contributing

_GRU953 Markdown_

Thank you for your interest in improving GRU953 Markdown. Contributions of all
sizes are welcome — from fixing a typo to proposing a new feature.

## Getting set up

1. Fork the `gru953-markdown` repository and clone your fork locally.
2. Install the Python dependencies listed in the project (see `requirements`),
   plus Tesseract OCR if you are working on OCR features.
3. Run the application with `python app.py` to preview your changes.

## Running tests and lint

Before opening a pull request, please run the project's checks and make sure
they pass:

- Run the test suite with `pytest`.
- Run the linter and fix any reported issues.

Pull requests are expected to keep **continuous integration (CI) green** — CI
is the automated set of checks that runs on every change.

## Branch naming

Create a branch from `master` for your work:

- `feature/<name>` — for new functionality.
- `fix/<name>` — for bug fixes.

## Commit messages

Use clear, Conventional-style commit messages, for example:

- `feat: add RTF input support`
- `fix: correct Bijoy-to-Unicode mapping`
- `docs: clarify build instructions`

## Pull request process

1. Keep each pull request focused on a single change.
2. Describe what you changed and why.
3. Ensure CI is green and address review feedback.
4. A maintainer will review and merge once the change is ready.

## Sign-off (DCO)

This project uses the **Developer Certificate of Origin (DCO) 1.1** — a short
statement that you have the right to submit your contribution. There is **no
Contributor Licence Agreement (CLA)** to sign.

Add a `Signed-off-by` line to each commit (the `-s` flag does this for you):

```
git commit -s -m "feat: your change"
```

This produces:

```
Signed-off-by: Your Name <your.email@example.com>
```

## Licensing (inbound = outbound)

Contributions are accepted under the same licence as the project itself
(**inbound = outbound**): code is licensed under Apache-2.0. By contributing,
you agree your work is provided under these terms.

## Code of Conduct

All participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

Maintainer: **Aninda Sundar Howlader (GRU-953)** — aninda.sh15@gmail.com

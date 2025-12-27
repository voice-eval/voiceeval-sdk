# Contributing to VoiceEval SDK

We love your input! We want to make contributing to VoiceEval as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Workflow

We use `uv` and `hatch` for dependency management and packaging.

1.  **Clone the repo:**

    ```bash
    git clone https://github.com/voiceeval/voiceeval-sdk.git
    cd voiceeval-sdk
    ```

2.  **Install dependencies:**

    ```bash
    # Install dev dependencies (includes pytest, etc.)
    uv sync
    ```

3.  **Run Tests:**

    ```bash
    uv run pytest
    ```

4.  **Linting & Formatting:**

    We recommend using `ruff` (if configured) or standard tools. Ensure your code is pythonic.

## Pull Requests

1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes.
5.  Issue that PR!

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

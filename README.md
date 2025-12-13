# scribbl-py

[![CI](https://github.com/JacobCoffee/scribbl-py/actions/workflows/ci.yml/badge.svg)](https://github.com/JacobCoffee/scribbl-py/actions/workflows/ci.yml)
[![Documentation](https://github.com/JacobCoffee/scribbl-py/actions/workflows/docs.yml/badge.svg)](https://jacobcoffee.github.io/scribbl-py)
[![PyPI version](https://img.shields.io/pypi/v/scribbl-py.svg)](https://pypi.org/project/scribbl-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/scribbl-py.svg)](https://pypi.org/project/scribbl-py/)
[![License](https://img.shields.io/github/license/JacobCoffee/scribbl-py)](https://github.com/JacobCoffee/scribbl-py/blob/main/LICENSE)

A Litestar-based API for drawing and whiteboard applications.

## Installation

```bash
pip install scribbl-py
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add scribbl-py
```

### Optional Dependencies

```bash
# With database support (PostgreSQL)
pip install scribbl-py[db]

# All extras
pip install scribbl-py[all]
```

## Quick Start

```python
from litestar import Litestar
import scribbl_py

app = Litestar([])
```

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/scribbl-py
cd scribbl-py

# Install development dependencies
make dev

# Install pre-commit hooks
make install-prek
```

### Common Commands

```bash
make help          # Show all available commands
make dev           # Install development dependencies
make test          # Run tests
make test-cov      # Run tests with coverage
make lint          # Run all linters
make fmt           # Format code
make type-check    # Run type checker
make docs          # Build documentation
make docs-serve    # Serve docs with live reload
make ci            # Run all CI checks locally
```

## Documentation

Full documentation is available at [jacobcoffee.github.io/scribbl-py](https://jacobcoffee.github.io/scribbl-py).

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes using conventional commits (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

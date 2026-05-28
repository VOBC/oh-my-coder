#!/bin/bash
cd /Users/vobc/oh-my-coder
rm -rf .coverage* htmlcov
python3 -m coverage run --source=src/commands/cli_package_manager -m pytest tests/test_cli_package_manager.py -o "addopts=-p no:xdist" --no-header -q
python3 -m coverage report --include="*/cli_package_manager.py"
python3 -m coverage html --include="*/cli_package_manager.py"
echo "Coverage HTML report generated in htmlcov/index.html"

# Contributing

Issues and pull requests are welcome. Never attach real Circle credentials,
tokens, watch identifiers, child names, coordinates, traffic captures, or
unredacted Home Assistant storage files.

## Local checks

Run these commands before submitting a pull request:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components tests
ruff check custom_components tests
ruff format --check custom_components tests
```

Use fully fictional API responses in tests. Changes to cloud behavior should
be documented without publishing account-specific payload values.

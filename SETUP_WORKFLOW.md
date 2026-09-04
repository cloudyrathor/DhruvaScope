# DhruvaScope Setup Workflow

## 1. Generate the project skeleton

Run `create_dhruvascope.py`.

## 2. Enter the project

```bash
cd DhruvaScope
```

## 3. Run environment setup

Copy `setup_dhruvascope.py` into the DhruvaScope directory and run:

```bash
python3 setup_dhruvascope.py
```

The script creates `.venv`, upgrades packaging tools, installs
`requirements.txt`, retries failed commands up to three times, and verifies
the important imports.

## 4. Activate

```bash
source .venv/bin/activate
```

## 5. Verify

```bash
python --version
pip list
```

## Important

Do not commit `.venv/`.

The repository `.gitignore` must contain:

```text
.venv/
```

Dependencies should be added to `requirements.txt` only when the project
actually needs them. Avoid installing a large collection of future libraries
at the beginning.

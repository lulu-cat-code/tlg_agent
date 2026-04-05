# TLG Agent

## New Pipeline

Input:

1. DOCX shell file
2. CSV file path (schema-only parse; header is enough)
3. TRT group column name

Flow:

1. `parser` parses DOCX structure and CSV attributes only
2. `planner` builds a generation plan and output contract
3. `mapper` uses LLM to infer group types, row formats, and DOCX->CSV mappings
4. `code_generator` uses LLM to generate executable R code
5. `validator` checks generated code against DOCX blueprint (rows/columns order constraints)
6. `reviewer` checks unresolved mappings and TODO markers (optional)
7. `runner` can execute generated `.R` later when data is available

## Generate R Code

`scripts/generate_r_from_docx.py` reads a DOCX shell, inspects the CSV header, uses the TRT group column to build mappings, and writes an executable `.R` script.

Usage:

```bash
python scripts/generate_r_from_docx.py <docx_filename> <csv_path> <trt_group_name> --data-dir <docx_dir> --output <output_r_file>
```

Parameter guide:

- `docx_filename`: DOCX shell filename under `--data-dir`, for example `shell_test_simple.docx`
- `csv_path`: CSV file path to use for schema parsing, for example `data/adsl.csv`
- `trt_group_name`: treatment column in the CSV, for example `TRT01A`
- `--data-dir`: directory that contains the DOCX shell file, default is `data`
- `--output`: output path for the generated R script
- `--model`: optional LLM model name, default is `gpt-4.1-mini`
- `--disable-reviewer`: optional flag to skip the reviewer stage

How to replace parameters:

- To use a different shell, replace the first positional argument
- To use a different CSV, replace the second positional argument
- To use a different treatment column, replace the third positional argument
- To change the generated R filename, replace the value passed to `--output`

```bash
export OPENAI_API_KEY=your_key_here
python scripts/generate_r_from_docx.py shell_test_simple.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_test_simple.R
```

Example with the expanded flow shell and augmented CSV:

```bash
python scripts/generate_r_from_docx.py shell_test_flow.docx data/_adsl+.csv TRT01A --data-dir data --output generated_shell_test_flow.R
```

Disable reviewer stage:

```bash
python scripts/generate_r_from_docx.py shell_test_simple.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_test_simple.R --disable-reviewer
```

## Run Generated R

```bash
Rscript generated_shell_test_simple.R
```

Example for the flow shell output:

```bash
Rscript generated_shell_test_flow.R 2>&1 | tee run_flow.log
```

## End-to-End (Copy/Paste)

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here

python scripts/generate_r_from_docx.py \
  shell_test_simple.docx \
  data/adsl.csv \
  TRT01A \
  --data-dir data \
  --output generated_shell_test_simple.R \
  --model gpt-4.1-mini

Rscript generated_shell_test_simple.R 2>&1 | tee run.log
```

## Module Entrypoints

- `src/parser.py`: `parse_docx_shell`, `parse_csv_schema`, `parse_inputs`
- `src/planner.py`: `build_generation_plan`
- `src/mapper.py`: `map_docx_fields_to_csv`
- `src/llm_agent.py`: `LLMDecisionEngine`
- `src/code_generator.py`: `generate_r_code`
- `src/reviewer.py`: `review_generation`
- `src/validator.py`: `validate_code_against_blueprint`
- `src/runner.py`: `run_r_script`
- `src/orchestrator.py`: `run_pipeline`

## Prompt Files

Prompts are decoupled in `prompts/`:

- `prompts/mapping_system.txt`
- `prompts/mapping_user.txt`
- `prompts/codegen_system.txt`
- `prompts/codegen_user.txt`

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
5. `validator` checks generated code against DOCX blueprint and enforces an R package allowlist
6. `reviewer` checks unresolved mappings and TODO markers (optional)
7. `runner` can execute generated `.R` later when data is available

## Generate R Code

`scripts/generate_r_from_docx.py` reads a DOCX shell, inspects the CSV header, uses the TRT group column to build mappings, and writes an executable `.R` script.

Usage:

```bash
python scripts/generate_r_from_docx.py <docx_filename> <csv_path> <trt_group_name> --data-dir <docx_dir> --output <output_r_file>
```

Parameter guide:

- `docx_filename`: DOCX shell filename under `--data-dir`, for example `shell_t_o5.docx`
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
python scripts/generate_r_from_docx.py shell_t_o5.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_t_o5.R
```

Example with the expanded flow shell and augmented CSV:

```bash
python scripts/generate_r_from_docx.py shell_t_o5_3.docx data/_adsl+.csv TRT01A --data-dir data --output generated_shell_t_o5_3.R
```

Disable reviewer stage:

```bash
python scripts/generate_r_from_docx.py shell_t_o5.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_t_o5.R --disable-reviewer
```

## Run Generated R

```bash
bash scripts/run_r_with_log.sh generated_shell_t_o5.R run.log
```

Example for the flow shell output:

```bash
bash scripts/run_r_with_log.sh generated_shell_t_o5_3.R run_flow.log
```

## End-to-End (Copy/Paste)

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here

python scripts/generate_r_from_docx.py \
  shell_t_o5.docx \
  data/adsl.csv \
  TRT01A \
  --data-dir data \
  --output generated_shell_t_o5.R \
  --model gpt-4.1-mini

bash scripts/run_r_with_log.sh generated_shell_t_o5.R run.log
```

## Run Shiny App

The Shiny UI is in [app.R](/Users/luluz/workspace/tlg_agent/app.R:1). Install the required R packages first:

```bash
Rscript -e 'install.packages(c("shiny", "jsonlite", "processx"), repos="https://cloud.r-project.org")'
```

Set your OpenAI API key in the same terminal session before starting the app:

```bash
export OPENAI_API_KEY=your_key_here
```

Start the app from the project root:

```bash
Rscript -e 'shiny::runApp("app.R", host="127.0.0.1", port=3839, launch.browser=TRUE)'
```

You can also pass the API key inline for a single run:

```bash
OPENAI_API_KEY=your_key_here Rscript -e 'shiny::runApp("app.R", host="127.0.0.1", port=3839, launch.browser=TRUE)'
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

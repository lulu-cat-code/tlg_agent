# TLG Agent

Generate executable R table scripts from a DOCX shell, a CSV schema, and a treatment column.

## Inputs

Required inputs:

1. DOCX shell file
2. CSV file path
3. Treatment group column name

The current pipeline expects all three inputs.

## Generate R

```bash
export OPENAI_API_KEY=your_key_here

python scripts/generate_r_from_docx.py \
  shell_t_o5.docx \
  data/adsl.csv \
  TRT01A \
  --data-dir data \
  --output generated_shell_t_o5.R
```

Example with another shell and CSV:

```bash
python scripts/generate_r_from_docx.py \
  shell_t_o5_3.docx \
  data/_adsl+.csv \
  TRT01A \
  --data-dir data \
  --output generated_shell_t_o5_3.R
```

## Run Generated R

```bash
Rscript generated_shell_t_o5.R 2>&1 | tee run.log
```

Example:

```bash
Rscript generated_shell_t_o5_3.R 2>&1 | tee run_flow.log
```

## Outputs

Typical outputs:

- `.R`: generated R script
- `.result.json`: structured pipeline result summary
- `.todo.md`: issues or follow-up checks for the generated output
- `run.log`: saved console output from running the generated R script

## Run Shiny App

Install required R packages:

```bash
Rscript -e 'install.packages(c("shiny", "jsonlite", "processx"), repos="https://cloud.r-project.org")'
```

Set your API key:

```bash
export OPENAI_API_KEY=your_key_here
```

Start the app:

```bash
Rscript -e 'shiny::runApp("app.R", host="127.0.0.1", port=3839, launch.browser=TRUE)'
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

- `prompts/mapping_system.txt`
- `prompts/mapping_user.txt`
- `prompts/codegen_system.txt`
- `prompts/codegen_user.txt`

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

```bash
export OPENAI_API_KEY=your_key_here
python scripts/generate_r_from_docx.py shell_test_simple.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_test_simple.R
```

Disable reviewer stage:

```bash
python scripts/generate_r_from_docx.py shell_test_simple.docx data/adsl.csv TRT01A --data-dir data --output generated_shell_test_simple.R --disable-reviewer
```

## Run Generated R

```bash
Rscript generated_shell_test_simple.R
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

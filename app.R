library(shiny)

make_result_path <- function(output_r_path) {
  sub("\\.R$", ".result.json", output_r_path)
}

make_todo_path <- function(output_r_path) {
  sub("\\.R$", ".todo.md", output_r_path)
}

make_status_path <- function(run_dir) {
  file.path(run_dir, "status.json")
}

make_events_path <- function(run_dir) {
  file.path(run_dir, "events.log")
}

safe_read_text <- function(path) {
  if (is.null(path) || !file.exists(path)) {
    return("")
  }
  paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
}

safe_read_json <- function(path) {
  if (is.null(path) || !file.exists(path)) {
    return(NULL)
  }
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

read_csv_columns <- function(path) {
  if (is.null(path) || !file.exists(path)) {
    return(character())
  }
  tryCatch(
    names(utils::read.csv(path, nrows = 0, check.names = FALSE)),
    error = function(e) character()
  )
}

write_json <- function(path, payload) {
  jsonlite::write_json(payload, path, auto_unbox = TRUE, pretty = TRUE)
}

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0) {
    return(y)
  }
  x
}

utc_now_iso <- function() {
  format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%d %H:%M:%S", tz = "UTC")
}

write_initial_job_files <- function(run_dir, model, output_r) {
  status_path <- make_status_path(run_dir)
  events_path <- make_events_path(run_dir)
  now <- utc_now_iso()
  payload <- list(
    job_id = basename(run_dir),
    job_type = "generate",
    status = "queued",
    stage = "queued",
    message = "Job submitted",
    started_at = now,
    updated_at = now,
    finished_at = NULL,
    error_message = NULL,
    result_available = FALSE,
    paths = list(
      job_dir = run_dir,
      events_log = events_path,
      output_r = output_r,
      result_json = make_result_path(output_r),
      todo_md = make_todo_path(output_r)
    ),
    stages = list(
      list(name = "queued", status = "running"),
      list(name = "parse", status = "pending"),
      list(name = "plan", status = "pending"),
      list(name = "map", status = "pending"),
      list(name = "generate", status = "pending"),
      list(name = "optimize", status = "pending"),
      list(name = "validate", status = "pending"),
      list(name = "review", status = "pending"),
      list(name = "done", status = "pending")
    )
  )
  write_json(status_path, payload)
  writeLines(
    c(
      sprintf("[%s] Job created", now),
      sprintf("[%s] Queued generate job for model %s", now, model)
    ),
    con = events_path,
    useBytes = TRUE
  )
  list(status_path = status_path, events_path = events_path)
}

format_stage_label <- function(name) {
  labels <- list(
    queued = "Queued",
    parse = "Parse Inputs",
    plan = "Build Plan",
    map = "Map Fields",
    generate = "Generate R",
    optimize = "Optimize R",
    validate = "Validate",
    review = "Review",
    done = "Done"
  )
  labels[[name]] %||% name
}

ui <- fluidPage(
  titlePanel("TLG Agent"),
  tags$style(HTML("
    .status-box { padding: 12px; border: 1px solid #d9d9d9; border-radius: 8px; background: #fafafa; margin-bottom: 12px; }
    .todo-box { white-space: pre-wrap; font-family: Menlo, Consolas, monospace; background: #fffdf5; border: 1px solid #ead9a4; border-radius: 8px; padding: 12px; }
    .code-box { white-space: pre-wrap; font-family: Menlo, Consolas, monospace; background: #f7f7f7; border: 1px solid #d9d9d9; border-radius: 8px; padding: 12px; max-height: 520px; overflow-y: auto; }
    .stage-list { margin: 12px 0 0 0; padding: 0; list-style: none; }
    .stage-item { display: flex; justify-content: space-between; padding: 8px 10px; border: 1px solid #d9d9d9; border-radius: 8px; background: #fff; margin-bottom: 8px; }
    .stage-name { font-weight: 600; }
    .stage-status { text-transform: uppercase; font-size: 12px; letter-spacing: 0.04em; }
    .stage-running .stage-status { color: #0b63ce; }
    .stage-done .stage-status { color: #1d7a34; }
    .stage-failed .stage-status { color: #b42318; }
    .stage-pending .stage-status { color: #667085; }
    .usage-table { width: 100%; border-collapse: collapse; background: #ffffff; margin-top: 12px; }
    .usage-table th, .usage-table td { border: 1px solid #d9d9d9; padding: 8px 10px; text-align: left; }
    .usage-table th { background: #f3f6fa; font-weight: 600; }
  ")),
  sidebarLayout(
    sidebarPanel(
      width = 4,
      fileInput("docx_file", "DOCX shell", accept = ".docx"),
      fileInput("csv_file", "CSV file", accept = ".csv"),
      selectizeInput(
        "trt_group",
        "TRT group",
        choices = NULL,
        selected = NULL,
        options = list(
          placeholder = "Upload a CSV to choose a treatment column",
          create = FALSE,
          maxOptions = 500,
          score = I("function(search) {
            var query = (search || '').toLowerCase();
            return function(item) {
              var text = ((item.text || item.value || '') + '').toLowerCase();
              if (!query.length) return 1;
              if (text.indexOf(query) === 0) return 2;
              if (text.indexOf(query) >= 0) return 1;
              return 0;
            };
          }")
        )
      ),
      textInput("model", "Model", value = "gpt-4.1-mini"),
      checkboxInput("disable_reviewer", "Disable reviewer", value = FALSE),
      actionButton("generate_btn", "Generate R", class = "btn-primary"),
      br(), br(),
      actionButton("run_btn", "Run R Script"),
      br(), br(),
      downloadButton("download_r", "Download R"),
      downloadButton("download_todo", "Download TODO")
    ),
    mainPanel(
      width = 8,
      h3("Pipeline Status"),
      uiOutput("status_ui"),
      h3("Pipeline Log"),
      uiOutput("events_ui"),
      h3("Token Usage"),
      uiOutput("usage_ui"),
      h3("Action Items"),
      uiOutput("todo_ui"),
      fluidRow(
        column(
          width = 6,
          h3("Generated R Script"),
          uiOutput("r_code_ui")
        ),
        column(
          width = 6,
          h3("Run Log"),
          uiOutput("run_log_ui")
        )
      )
    )
  )
)

server <- function(input, output, session) {
  if (!requireNamespace("processx", quietly = TRUE)) {
    stop("The 'processx' package is required. Install it with install.packages('processx').")
  }

  work_dir <- getwd()
  app_data_dir <- file.path(work_dir, "shiny_runs")
  if (!dir.exists(app_data_dir)) {
    dir.create(app_data_dir, recursive = TRUE, showWarnings = FALSE)
  }

  generated_r_path <- reactiveVal(NULL)
  result_json_path <- reactiveVal(NULL)
  todo_md_path <- reactiveVal(NULL)
  run_log_path <- reactiveVal(NULL)
  status_json_path <- reactiveVal(NULL)
  events_log_path <- reactiveVal(NULL)
  input_csv_path <- reactiveVal(NULL)
  command_output <- reactiveVal("")

  observeEvent(input$csv_file, {
    req(input$csv_file)
    columns <- read_csv_columns(input$csv_file$datapath)
    default_choice <- if ("TRT01A" %in% columns) "TRT01A" else if (length(columns) > 0) columns[[1]] else ""
    updateSelectizeInput(
      session,
      "trt_group",
      choices = columns,
      selected = default_choice,
      server = TRUE
    )
  }, ignoreInit = TRUE)

  observeEvent(input$generate_btn, {
    req(input$docx_file, input$csv_file, nzchar(input$trt_group))

    run_id <- format(Sys.time(), "%Y%m%d_%H%M%S")
    run_dir <- file.path(app_data_dir, run_id)
    dir.create(run_dir, recursive = TRUE, showWarnings = FALSE)

    docx_target <- file.path(run_dir, input$docx_file$name)
    csv_target <- file.path(run_dir, input$csv_file$name)
    file.copy(input$docx_file$datapath, docx_target, overwrite = TRUE)
    file.copy(input$csv_file$datapath, csv_target, overwrite = TRUE)

    output_r <- file.path(run_dir, "generated_shell.R")
    initial_files <- write_initial_job_files(run_dir, input$model, output_r)
    status_path <- initial_files$status_path
    events_path <- initial_files$events_path
    args <- c(
      file.path("scripts", "run_generate_job.py"),
      "--job-dir", run_dir,
      "--docx-filename", basename(docx_target),
      "--csv-path", csv_target,
      "--trt-group-name", input$trt_group,
      "--model", input$model
    )
    if (isTRUE(input$disable_reviewer)) {
      args <- c(args, "--disable-reviewer")
    }

    launch_ok <- tryCatch(
      {
        processx::process$new(
          command = "python",
          args = args,
          stdout = events_path,
          stderr = events_path,
          supervise = FALSE,
          cleanup = FALSE
        )
        TRUE
      },
      warning = function(w) FALSE,
      error = function(e) FALSE
    )
    command_output(if (launch_ok) "Generate job submitted." else "Failed to launch generate job.")

    generated_r_path(output_r)
    result_json_path(make_result_path(output_r))
    status_json_path(status_path)
    events_log_path(events_path)
    todo_candidate <- make_todo_path(output_r)
    todo_md_path(if (file.exists(todo_candidate)) todo_candidate else NULL)
    run_log_path(NULL)
    input_csv_path(csv_target)

    if (!launch_ok) {
      write_json(
        status_path,
        list(
          job_id = basename(run_dir),
          job_type = "generate",
          status = "failed",
          stage = "queued",
          message = "Failed to launch generate job",
          started_at = utc_now_iso(),
          updated_at = utc_now_iso(),
          finished_at = utc_now_iso(),
          error_message = "Unable to start background Python process.",
          result_available = FALSE,
          paths = list(
            job_dir = run_dir,
            events_log = events_path,
            output_r = output_r,
            result_json = make_result_path(output_r),
            todo_md = make_todo_path(output_r)
          ),
          stages = list(
            list(name = "queued", status = "failed"),
            list(name = "parse", status = "pending"),
            list(name = "plan", status = "pending"),
            list(name = "map", status = "pending"),
            list(name = "generate", status = "pending"),
            list(name = "optimize", status = "pending"),
            list(name = "validate", status = "pending"),
            list(name = "review", status = "pending"),
            list(name = "done", status = "failed")
          )
        )
      )
    }
  })

  observeEvent(input$run_btn, {
    req(generated_r_path(), file.exists(generated_r_path()))
    req(input_csv_path(), file.exists(input_csv_path()))

    log_path <- file.path(dirname(generated_r_path()), "run.log")
    cmd <- paste(
      "Rscript",
      shQuote(generated_r_path()),
      shQuote(input_csv_path()),
      ">",
      shQuote(log_path),
      "2>&1"
    )
    system(cmd)
    if (file.exists(input_csv_path())) {
      unlink(input_csv_path())
    }
    input_csv_path(NULL)
    run_log_path(log_path)
  })

  output$status_ui <- renderUI({
    status <- safe_read_json(status_json_path())
    if (is.null(status)) {
      text <- if (nzchar(command_output())) command_output() else "No pipeline run yet."
      return(div(class = "status-box", tags$pre(text)))
    }

    if (!(status$status %in% c("succeeded", "failed", "cancelled"))) {
      invalidateLater(1000, session)
    }

    stage_items <- lapply(status$stages %||% list(), function(item) {
      stage_status <- item$status %||% "pending"
      tags$li(
        class = paste("stage-item", paste0("stage-", stage_status)),
        tags$span(class = "stage-name", format_stage_label(item$name %||% "")),
        tags$span(class = "stage-status", stage_status)
      )
    })

    result <- safe_read_json(result_json_path())
    summary_lines <- c(
      if (!is.null(status$message) && nzchar(status$message) && !(status$stage %||% "" %in% c("queued", "done"))) {
        paste0("Now: ", status$message)
      } else NULL,
      if (!is.null(status$error_message) && nzchar(status$error_message)) {
        paste0("Error: ", status$error_message)
      } else NULL,
      if (!is.null(result) && length(result$issues) > 0) {
        paste("Issues:", paste(result$issues, collapse = " | "))
      } else NULL,
      if (!is.null(result) && length(result$warnings) > 0) {
        paste("Warnings:", paste(result$warnings, collapse = " | "))
      } else NULL
    )

    div(
      class = "status-box",
      if (length(summary_lines) > 0) tags$pre(paste(summary_lines, collapse = "\n")),
      tags$ul(class = "stage-list", stage_items)
    )
  })

  output$events_ui <- renderUI({
    path <- events_log_path()
    status <- safe_read_json(status_json_path())
    if (!is.null(status) && !(status$status %in% c("succeeded", "failed", "cancelled"))) {
      invalidateLater(1000, session)
    }
    if (is.null(path) || !file.exists(path)) {
      return(div(class = "status-box", "No pipeline log yet."))
    }
    div(class = "code-box", safe_read_text(path))
  })

  output$usage_ui <- renderUI({
    status <- safe_read_json(status_json_path())
    if (!is.null(status) && !(status$status %in% c("succeeded", "failed", "cancelled"))) {
      invalidateLater(1000, session)
    }
    result <- safe_read_json(result_json_path())
    usage <- if (is.null(result)) NULL else result$usage
    if (is.null(usage)) {
      return(div(class = "status-box", "Token usage will appear after a completed LLM call."))
    }

    rows <- list(
      tags$tr(
        tags$th("Prompt Tokens"),
        tags$th("Completion Tokens"),
        tags$th("Total Tokens")
      ),
      tags$tr(
        tags$td(as.character(usage$total_prompt_tokens %||% 0)),
        tags$td(as.character(usage$total_completion_tokens %||% 0)),
        tags$td(as.character(usage$total_tokens %||% 0))
      )
    )

    div(
      class = "status-box",
      do.call(tags$table, c(list(class = "usage-table"), rows))
    )
  })

  output$todo_ui <- renderUI({
    status <- safe_read_json(status_json_path())
    if (!is.null(status) && !(status$status %in% c("succeeded", "failed", "cancelled"))) {
      invalidateLater(1000, session)
    }
    path <- todo_md_path()
    if (is.null(path) || !file.exists(path)) {
      return(div(class = "status-box", "No action items. You can run the generated R script."))
    }
    div(class = "todo-box", safe_read_text(path))
  })

  output$r_code_ui <- renderUI({
    status <- safe_read_json(status_json_path())
    if (!is.null(status) && !(status$status %in% c("succeeded", "failed", "cancelled"))) {
      invalidateLater(1000, session)
    }
    path <- generated_r_path()
    if (is.null(path) || !file.exists(path)) {
      return(div(class = "status-box", "No generated R script yet."))
    }
    div(class = "code-box", safe_read_text(path))
  })

  output$run_log_ui <- renderUI({
    path <- run_log_path()
    if (is.null(path) || !file.exists(path)) {
      return(div(class = "status-box", "No run log yet."))
    }
    div(class = "code-box", safe_read_text(path))
  })

  output$download_r <- downloadHandler(
    filename = function() {
      "generated_shell.R"
    },
    content = function(file) {
      req(generated_r_path(), file.exists(generated_r_path()))
      file.copy(generated_r_path(), file, overwrite = TRUE)
    }
  )

  output$download_todo <- downloadHandler(
    filename = function() {
      "generated_shell.todo.md"
    },
    content = function(file) {
      req(todo_md_path(), file.exists(todo_md_path()))
      file.copy(todo_md_path(), file, overwrite = TRUE)
    }
  )
}

shinyApp(ui, server)

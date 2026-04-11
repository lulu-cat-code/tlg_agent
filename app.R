library(shiny)

make_result_path <- function(output_r_path) {
  sub("\\.R$", ".result.json", output_r_path)
}

make_todo_path <- function(output_r_path) {
  sub("\\.R$", ".todo.md", output_r_path)
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

ui <- fluidPage(
  titlePanel("TLG Agent"),
  tags$style(HTML("
    .status-box { padding: 12px; border: 1px solid #d9d9d9; border-radius: 8px; background: #fafafa; margin-bottom: 12px; }
    .todo-box { white-space: pre-wrap; font-family: Menlo, Consolas, monospace; background: #fffdf5; border: 1px solid #ead9a4; border-radius: 8px; padding: 12px; }
    .code-box { white-space: pre-wrap; font-family: Menlo, Consolas, monospace; background: #f7f7f7; border: 1px solid #d9d9d9; border-radius: 8px; padding: 12px; max-height: 520px; overflow-y: auto; }
  ")),
  sidebarLayout(
    sidebarPanel(
      width = 4,
      fileInput("docx_file", "DOCX shell", accept = ".docx"),
      fileInput("csv_file", "CSV file", accept = ".csv"),
      textInput("trt_group", "TRT group", value = "TRT01A"),
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
  work_dir <- getwd()
  app_data_dir <- file.path(work_dir, "shiny_runs")
  if (!dir.exists(app_data_dir)) {
    dir.create(app_data_dir, recursive = TRUE, showWarnings = FALSE)
  }

  generated_r_path <- reactiveVal(NULL)
  result_json_path <- reactiveVal(NULL)
  todo_md_path <- reactiveVal(NULL)
  run_log_path <- reactiveVal(NULL)
  command_output <- reactiveVal("")

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
    disable_flag <- if (isTRUE(input$disable_reviewer)) "--disable-reviewer" else ""
    cmd <- paste(
      "python",
      "scripts/generate_r_from_docx.py",
      shQuote(basename(docx_target)),
      shQuote(csv_target),
      shQuote(input$trt_group),
      "--data-dir",
      shQuote(run_dir),
      "--output",
      shQuote(output_r),
      "--model",
      shQuote(input$model),
      disable_flag
    )

    output_lines <- tryCatch(
      system(cmd, intern = TRUE, ignore.stderr = FALSE),
      warning = function(w) w$message,
      error = function(e) conditionMessage(e)
    )
    command_output(paste(output_lines, collapse = "\n"))

    generated_r_path(output_r)
    result_json_path(make_result_path(output_r))
    todo_candidate <- make_todo_path(output_r)
    todo_md_path(if (file.exists(todo_candidate)) todo_candidate else NULL)
    run_log_path(NULL)
  })

  observeEvent(input$run_btn, {
    req(generated_r_path(), file.exists(generated_r_path()))

    log_path <- file.path(dirname(generated_r_path()), "run.log")
    cmd <- paste(
      "Rscript",
      shQuote(generated_r_path()),
      ">",
      shQuote(log_path),
      "2>&1"
    )
    system(cmd)
    run_log_path(log_path)
  })

  output$status_ui <- renderUI({
    result <- safe_read_json(result_json_path())
    if (is.null(result)) {
      text <- if (nzchar(command_output())) command_output() else "No pipeline run yet."
      return(div(class = "status-box", tags$pre(text)))
    }

    status_text <- paste(
      paste0("pipeline_success: ", result$pipeline_success),
      paste0("review_status: ", result$review_status),
      if (!is.null(result$error_message) && nzchar(result$error_message)) paste0("error_message: ", result$error_message) else NULL,
      if (length(result$warnings) > 0) paste("warnings:", paste(result$warnings, collapse = " | ")) else NULL,
      if (length(result$issues) > 0) paste("issues:", paste(result$issues, collapse = " | ")) else NULL,
      sep = "\n"
    )

    div(
      class = "status-box",
      tags$pre(status_text),
      if (nzchar(command_output())) tags$details(
        tags$summary("CLI output"),
        tags$pre(command_output())
      )
    )
  })

  output$todo_ui <- renderUI({
    path <- todo_md_path()
    if (is.null(path) || !file.exists(path)) {
      return(div(class = "status-box", "No action items. You can run the generated R script."))
    }
    div(class = "todo-box", safe_read_text(path))
  })

  output$r_code_ui <- renderUI({
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

library(data.table)
library(stringr)
library(stats)

# Helper functions
normalize_label <- function(x) {
  x <- tolower(x)
  x <- trimws(x)
  x <- str_replace_all(x, "[-–—]", "-") # normalize hyphens
  x
}

format_count <- function(n) {
  as.character(n)
}

format_mean_sd <- function(x) {
  if(length(x) == 0) return(NA_character_)
  m <- mean(x, na.rm=TRUE)
  s <- sd(x, na.rm=TRUE)
  if(is.na(m) || is.na(s)) return(NA_character_)
  sprintf("%.1f (%.1f)", m, s)
}

format_median <- function(x) {
  if(length(x) == 0) return(NA_character_)
  med <- median(x, na.rm=TRUE)
  if(is.na(med)) return(NA_character_)
  as.character(med)
}

format_min_max <- function(x) {
  if(length(x) == 0) return(NA_character_)
  mn <- min(x, na.rm=TRUE)
  mx <- max(x, na.rm=TRUE)
  if(is.na(mn) || is.na(mx)) return(NA_character_)
  sprintf("%s-%s", mn, mx)
}

format_n_pct <- function(n, total) {
  if(total == 0) return("0 (0.0%)")
  pct <- 100 * n / total
  sprintf("%d (%.1f%%)", n, pct)
}

print_text_table <- function(mat) {
  widths <- apply(mat, 2, function(col) max(nchar(col, type="width"), na.rm=TRUE))
  for(r in seq_len(nrow(mat))) {
    cells <- character(ncol(mat))
    for(c in seq_len(ncol(mat))) {
      cells[c] <- format(mat[r, c], width=widths[c], justify="left")
    }
    cat(paste(cells, collapse=" "), "\n", sep="")
  }
}

# Read mapped_plan elements from environment
csv_path <- "data/adsl.csv"
trt_group <- "TRT01A"
tables <- list(
  list(
    table_index=1,
    columns=c("Treatment A", "Treatment B"),
    ordered_rows=list(
      list(kind="group_header", label="Age (yr)"),
      list(kind="data_row", group="Age (yr)", label="n", format_hint="count"),
      list(kind="data_row", group="Age (yr)", label="Mean (SD)", format_hint="mean_sd"),
      list(kind="data_row", group="Age (yr)", label="Median", format_hint="median"),
      list(kind="data_row", group="Age (yr)", label="Min-max", format_hint="min_max"),
      list(kind="group_header", label="Age group (yr)"),
      list(kind="data_row", group="Age group (yr)", label="n", format_hint="count"),
      list(kind="data_row", group="Age group (yr)", label="18–40", format_hint="n_pct"),
      list(kind="data_row", group="Age group (yr)", label="41–64", format_hint="n_pct"),
      list(kind="data_row", group="Age group (yr)", label="65", format_hint="n_pct"),
      list(kind="group_header", label="Sex"),
      list(kind="data_row", group="Sex", label="n", format_hint="count"),
      list(kind="data_row", group="Sex", label="Male", format_hint="n_pct"),
      list(kind="data_row", group="Sex", label="Female", format_hint="n_pct"),
      list(kind="group_header", label="Ethnicity"),
      list(kind="data_row", group="Ethnicity", label="n", format_hint="count"),
      list(kind="data_row", group="Ethnicity", label="Hispanic or Latino", format_hint="n_pct"),
      list(kind="data_row", group="Ethnicity", label="Not Hispanic or Latino", format_hint="n_pct"),
      list(kind="group_header", label="Race"),
      list(kind="data_row", group="Race", label="n", format_hint="count"),
      list(kind="data_row", group="Race", label="American Indian or Alaska Native", format_hint="n_pct"),
      list(kind="data_row", group="Race", label="Asian", format_hint="n_pct"),
      list(kind="data_row", group="Race", label="Black or African American", format_hint="n_pct"),
      list(kind="data_row", group="Race", label="Native Hawaiian or other Pacific Islander", format_hint="n_pct"),
      list(kind="data_row", group="Race", label="White", format_hint="n_pct")
    ),
    group_info=list(
      `Age (yr)`=list(group_type="continuous", subrows=c("n", "Mean (SD)", "Median", "Min-max")),
      `Age group (yr)`=list(group_type="categorical", subrows=c("n", "18–40", "41–64", "65")),
      Sex=list(group_type="categorical", subrows=c("n", "Male", "Female")),
      Ethnicity=list(group_type="categorical", subrows=c("n", "Hispanic or Latino", "Not Hispanic or Latino")),
      Race=list(group_type="categorical", subrows=c("n", "American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or other Pacific Islander", "White"))
    )
  )
)
mapping_tasks <- list(
  list(table_index=1, group_name="Age (yr)", group_slug="age_yr", group_type="continuous", candidate_csv_column="AGE", category_value_map=list(), confidence=0.95, reason="Age is a numeric continuous variable; CSV has AGE column matching group name"),
  list(table_index=1, group_name="Age group (yr)", group_slug="age_group_yr", group_type="categorical", candidate_csv_column="AGEGR1", category_value_map=list(), confidence=0.9, reason="Age group categories correspond to AGEGR1 categorical variable in CSV"),
  list(table_index=1, group_name="Sex", group_slug="sex", group_type="categorical", candidate_csv_column="SEX", category_value_map=list(), confidence=0.95, reason="Sex categories match SEX column in CSV"),
  list(table_index=1, group_name="Ethnicity", group_slug="ethnicity", group_type="categorical", candidate_csv_column="ETHNIC", category_value_map=list(), confidence=0.9, reason="Ethnicity categories correspond to ETHNIC column in CSV"),
  list(table_index=1, group_name="Race", group_slug="race", group_type="categorical", candidate_csv_column="RACE", category_value_map=list(), confidence=0.95, reason="Race categories correspond to RACE column in CSV")
)

# Read data
data <- fread(csv_path)

# Normalize treatment group column
data[[trt_group]] <- as.character(data[[trt_group]])

# Determine unique treatment levels
trt_levels <- unique(data[[trt_group]])

# Process each table
for(tbl in tables) {
  cat(sprintf("Table %d: %s\n", tbl$table_index, "Demographics and Baseline Characteristics: Safety Population"))
  docx_columns <- tbl$columns

  # Map DOCX columns to treatment levels
  # Try exact match first
  trt_map <- rep(NA_character_, length(docx_columns))
  for(i in seq_along(docx_columns)) {
    col_label <- docx_columns[i]
    # Exact match
    if(col_label %in% trt_levels) {
      trt_map[i] <- col_label
    }
  }
  # Fill missing by position fallback
  for(i in seq_along(trt_map)) {
    if(is.na(trt_map[i]) && i <= length(trt_levels)) {
      trt_map[i] <- trt_levels[i]
    }
  }

  # Build display column headers with actual N values
  display_columns <- docx_columns
  for(i in seq_along(docx_columns)) {
    trt_val <- trt_map[i]
    if(!is.na(trt_val)) {
      n_trt <- sum(data[[trt_group]] == trt_val, na.rm=TRUE)
      display_columns[i] <- sprintf("%s (N=%d)", docx_columns[i], n_trt)
    }
  }

  # Prepare output matrix
  n_rows <- length(tbl$ordered_rows)
  n_cols <- length(docx_columns) + 1 # +1 for row label
  out_mat <- matrix(NA_character_, nrow=n_rows, ncol=n_cols)
  colnames(out_mat) <- c(" ", display_columns)

  # Fill row labels
  for(r in seq_len(n_rows)) {
    rowinfo <- tbl$ordered_rows[[r]]
    if(identical(rowinfo$kind, "group_header")) {
      out_mat[r,1] <- rowinfo$label
    } else {
      out_mat[r,1] <- paste0("  ", rowinfo$label)
    }
  }

  # Helper: get mapping task for group
  get_mapping_task <- function(group_name) {
    for(mt in mapping_tasks) {
      if(mt$table_index == tbl$table_index && mt$group_name == group_name) return(mt)
    }
    NULL
  }

  # For each data row, fill values
  for(r in seq_len(n_rows)) {
    rowinfo <- tbl$ordered_rows[[r]]
    if(rowinfo$kind == "group_header") {
      # Just label row, no data
      next
    }
    group_name <- rowinfo$group
    label <- rowinfo$label
    format_hint <- rowinfo$format_hint

    mt <- get_mapping_task(group_name)
    if(is.null(mt)) {
      # No mapping task for this group
      for(c in seq_along(docx_columns)) {
        out_mat[r, c+1] <- "TODO: no mapping task"
      }
      next
    }

    csv_col <- mt$candidate_csv_column
    group_type <- mt$group_type
    cat_map <- mt$category_value_map

    # Subset data by treatment
    for(c in seq_along(docx_columns)) {
      trt_val <- trt_map[c]
      if(is.na(trt_val)) {
        out_mat[r, c+1] <- "TODO: no treatment mapping"
        next
      }
      subdata <- data[data[[trt_group]] == trt_val, , drop=FALSE]

      if(group_type == "continuous") {
        x <- subdata[[csv_col]]
        if(label == "n") {
          val <- format_count(sum(!is.na(x)))
        } else if(label == "Mean (SD)") {
          val <- format_mean_sd(x)
        } else if(label == "Median") {
          val <- format_median(x)
        } else if(label == "Min-max") {
          val <- format_min_max(x)
        } else {
          val <- "TODO: unknown continuous label"
        }
        out_mat[r, c+1] <- val
      } else if(group_type == "categorical") {
        # For categorical, get counts and percentages
        # First row 'n' is total non-missing count
        if(label == "n") {
          n_val <- sum(!is.na(subdata[[csv_col]]))
          out_mat[r, c+1] <- format_count(n_val)
        } else {
          # Map label to category value
          cat_val <- NULL
          if(length(cat_map) > 0) {
            # Try category_value_map
            cat_val <- cat_map[[label]]
          }
          if(is.null(cat_val)) {
            # fallback: normalize and match
            norm_label <- normalize_label(label)
            # unique categories in data
            cats <- unique(subdata[[csv_col]])
            cats_norm <- sapply(cats, normalize_label)
            idx <- which(cats_norm == norm_label)
            if(length(idx) == 1) {
              cat_val <- cats[idx]
            } else {
              cat_val <- NULL
            }
          }
          if(is.null(cat_val)) {
            out_mat[r, c+1] <- "TODO: no category mapping"
          } else {
            n_cat <- sum(subdata[[csv_col]] == cat_val, na.rm=TRUE)
            n_total <- sum(!is.na(subdata[[csv_col]]))
            val <- format_n_pct(n_cat, n_total)
            out_mat[r, c+1] <- val
          }
        }
      } else {
        out_mat[r, c+1] <- "TODO: unknown group_type"
      }
    }
  }

  # Print table
  out_mat[is.na(out_mat)] <- ""
  print_text_table(rbind(colnames(out_mat), out_mat))
  cat("\n")
}

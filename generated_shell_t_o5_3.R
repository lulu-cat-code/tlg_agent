library(data.table)
library(stringr)
library(stats)

# Helper functions
normalize_label <- function(x) {
  x <- tolower(x)
  x <- trimws(x)
  x <- gsub("[-–—]+", "-", x) # normalize hyphens
  x
}

format_count <- function(n) {
  as.character(n)
}

format_mean_sd <- function(x) {
  if (length(x) == 0) return("")
  m <- mean(x, na.rm=TRUE)
  s <- sd(x, na.rm=TRUE)
  if (is.na(m) || is.na(s)) return("")
  sprintf("%.1f (%.1f)", m, s)
}

format_median <- function(x) {
  if (length(x) == 0) return("")
  med <- median(x, na.rm=TRUE)
  if (is.na(med)) return("")
  if (med == floor(med)) sprintf("%d", med) else sprintf("%.1f", med)
}

format_min_max <- function(x) {
  if (length(x) == 0) return("")
  mn <- min(x, na.rm=TRUE)
  mx <- max(x, na.rm=TRUE)
  if (is.na(mn) || is.na(mx)) return("")
  if (mn == floor(mn) && mx == floor(mx)) {
    sprintf("%d–%d", mn, mx)
  } else {
    sprintf("%.1f–%.1f", mn, mx)
  }
}

format_n_pct <- function(n, total) {
  if (total == 0) return("")
  pct <- 100 * n / total
  sprintf("%d (%.1f%%)", n, pct)
}

# Read CSV path from mapped_plan
csv_path <- "data/_adsl+.csv"  # from mapped_plan.csv_schema.csv_path

# Read data
data <- fread(csv_path, data.table=FALSE)

# Treatment group column
trt_group <- "TRT01A"  # from mapped_plan.trt_group_name

# Extract unique treatment levels
trt_levels <- unique(data[[trt_group]])

# DOCX columns from mapped_plan.tables[[1]]
docx_columns <- c("Treatment A", "Treatment B")

# Map DOCX columns to actual treatment levels
# Try exact match first
trt_map <- character(length(docx_columns))
for (i in seq_along(docx_columns)) {
  col <- docx_columns[i]
  # Exact match ignoring case and whitespace
  matched <- trt_levels[tolower(trt_levels) == tolower(col)]
  if (length(matched) == 1) {
    trt_map[i] <- matched
  } else if (i <= length(trt_levels)) {
    # fallback to position
    trt_map[i] <- trt_levels[i]
  } else {
    trt_map[i] <- NA_character_
  }
}

# Group sizes from mapped_plan.tables[[1]]
group_sizes <- list("Treatment A" = NA, "Treatment B" = NA)  # "nnn" placeholder
# Try to get actual group sizes from data
for (i in seq_along(docx_columns)) {
  trt_val <- trt_map[i]
  if (!is.na(trt_val)) {
    group_sizes[[docx_columns[i]]] <- sum(data[[trt_group]] == trt_val, na.rm=TRUE)
  }
}

# Build treatment display headers with group sizes
treatment_headers <- character(length(docx_columns))
for (i in seq_along(docx_columns)) {
  size <- group_sizes[[docx_columns[i]]]
  if (is.na(size)) {
    treatment_headers[i] <- docx_columns[i]
  } else {
    treatment_headers[i] <- sprintf("%s (N=%d)", docx_columns[i], size)
  }
}

# Mapping tasks from mapped_plan.mapping_tasks
mapping_tasks <- list(
  list(table_index=1, group_name="Age (yr)", group_type="continuous", candidate_csv_column="AGE", category_value_map=list()),
  list(table_index=1, group_name="Age group (yr)", group_type="categorical", candidate_csv_column="AGEGR1", category_value_map=list()),
  list(table_index=1, group_name="Diabetes", group_type="categorical", candidate_csv_column="Diabetes", category_value_map=list()),
  list(table_index=1, group_name="Kidney disease", group_type="categorical", candidate_csv_column="Disease_kidney", category_value_map=list()),
  list(table_index=1, group_name="Blood pressure at baseline", group_type="continuous", candidate_csv_column="baseline_bp", category_value_map=list())
)

# Table ordered rows from mapped_plan.tables[[1]]
table_ordered_rows <- list(
  list(kind="group_header", label="Age (yr)"),
  list(kind="data_row", group="Age (yr)", label="n", format_hint="count"),
  list(kind="data_row", group="Age (yr)", label="Mean (SD)", format_hint="mean_sd"),
  list(kind="data_row", group="Age (yr)", label="Median", format_hint="median"),
  list(kind="data_row", group="Age (yr)", label="Min–max", format_hint="min_max"),
  list(kind="group_header", label="Age group (yr)"),
  list(kind="data_row", group="Age group (yr)", label="n", format_hint="count"),
  list(kind="data_row", group="Age group (yr)", label="18–40", format_hint="n_pct"),
  list(kind="data_row", group="Age group (yr)", label="41–64", format_hint="n_pct"),
  list(kind="data_row", group="Age group (yr)", label="≥65", format_hint="n_pct"),
  list(kind="group_header", label="Diabetes"),
  list(kind="data_row", group="Diabetes", label="n", format_hint="count"),
  list(kind="data_row", group="Diabetes", label="Yes", format_hint="n_pct"),
  list(kind="data_row", group="Diabetes", label="No", format_hint="n_pct"),
  list(kind="group_header", label="Kidney disease"),
  list(kind="data_row", group="Kidney disease", label="n", format_hint="count"),
  list(kind="data_row", group="Kidney disease", label="Stage 1", format_hint="n_pct"),
  list(kind="data_row", group="Kidney disease", label="Stage 2", format_hint="n_pct"),
  list(kind="data_row", group="Kidney disease", label="Stage 3", format_hint="n_pct"),
  list(kind="group_header", label="Blood pressure at baseline"),
  list(kind="data_row", group="Blood pressure at baseline", label="n", format_hint="count"),
  list(kind="data_row", group="Blood pressure at baseline", label="Mean (SD)", format_hint="mean_sd"),
  list(kind="data_row", group="Blood pressure at baseline", label="Median", format_hint="median"),
  list(kind="data_row", group="Blood pressure at baseline", label="Min–max", format_hint="min_max")
)

# Group info from mapped_plan.tables[[1]]
group_info <- list(
  "Age (yr)" = list(group_type="continuous", subrows=c("n", "Mean (SD)", "Median", "Min–max")),
  "Age group (yr)" = list(group_type="categorical", subrows=c("n", "18–40", "41–64", "≥65")),
  "Diabetes" = list(group_type="categorical", subrows=c("n", "Yes", "No")),
  "Kidney disease" = list(group_type="categorical", subrows=c("n", "Stage 1", "Stage 2", "Stage 3")),
  "Blood pressure at baseline" = list(group_type="continuous", subrows=c("n", "Mean (SD)", "Median", "Min–max"))
)

# Normalize function for matching category labels
normalize_cat_label <- function(x) {
  x <- tolower(x)
  x <- trimws(x)
  x <- gsub("[-–—]+", "-", x)
  x
}

# Find mapping task by group name
find_mapping_task <- function(group_name) {
  for (mt in mapping_tasks) {
    if (mt$group_name == group_name) return(mt)
  }
  NULL
}

# Prepare output tables list
output_tables <- list()

# Process table 1
# Initialize output matrix: rows = length(table_ordered_rows), cols = length(docx_columns)+1 (row label col)
n_rows <- length(table_ordered_rows)
n_cols <- length(docx_columns) + 1
output_mat <- matrix("", nrow=n_rows, ncol=n_cols)

# Fill row label column (first col) with indentation for data rows
for (i in seq_len(n_rows)) {
  row <- table_ordered_rows[[i]]
  if (row$kind == "group_header") {
    output_mat[i, 1] <- row$label
  } else if (row$kind == "data_row") {
    # indent child rows by 2 spaces
    output_mat[i, 1] <- paste0("  ", row$label)
  } else {
    output_mat[i, 1] <- row$label
  }
}

# Fill treatment header row (not part of ordered_rows, print separately)
# We'll print headers separately

# Function to get mapping task for a group
get_mapping_for_group <- function(group_name) {
  mt <- find_mapping_task(group_name)
  if (is.null(mt)) stop(paste("TODO: mapping task missing for group", group_name))
  mt
}

# For each data row, fill values per treatment
for (i in seq_len(n_rows)) {
  row <- table_ordered_rows[[i]]
  if (row$kind != "data_row") next
  group_name <- row$group
  label <- row$label
  format_hint <- row$format_hint
  mt <- get_mapping_for_group(group_name)
  csv_col <- mt$candidate_csv_column
  group_type <- mt$group_type
  cat_map <- mt$category_value_map

  # For each treatment column
  for (j in seq_along(docx_columns)) {
    trt_val <- trt_map[j]
    if (is.na(trt_val)) {
      output_mat[i, j+1] <- "" # no treatment mapping
      next
    }
    # Subset data for this treatment
    subdata <- data[data[[trt_group]] == trt_val, , drop=FALSE]

    # Compute value based on format_hint
    val <- ""
    if (format_hint == "count") {
      # Count of non-missing values in candidate column
      if (!(csv_col %in% names(subdata))) {
        val <- paste0("TODO: missing column '", csv_col, "'")
      } else {
        val <- format_count(sum(!is.na(subdata[[csv_col]])))
      }
    } else if (format_hint == "mean_sd") {
      if (!(csv_col %in% names(subdata))) {
        val <- paste0("TODO: missing column '", csv_col, "'")
      } else {
        vals <- suppressWarnings(as.numeric(subdata[[csv_col]]))
        val <- format_mean_sd(vals)
      }
    } else if (format_hint == "median") {
      if (!(csv_col %in% names(subdata))) {
        val <- paste0("TODO: missing column '", csv_col, "'")
      } else {
        vals <- suppressWarnings(as.numeric(subdata[[csv_col]]))
        val <- format_median(vals)
      }
    } else if (format_hint == "min_max") {
      if (!(csv_col %in% names(subdata))) {
        val <- paste0("TODO: missing column '", csv_col, "'")
      } else {
        vals <- suppressWarnings(as.numeric(subdata[[csv_col]]))
        val <- format_min_max(vals)
      }
    } else if (format_hint == "n_pct") {
      # For categorical rows, count and percent of category matching label
      if (!(csv_col %in% names(subdata))) {
        val <- paste0("TODO: missing column '", csv_col, "'")
      } else {
        # Determine category value to match
        cat_val <- NULL
        if (length(cat_map) > 0) {
          # Try category_value_map
          cat_val <- cat_map[[label]]
        }
        if (is.null(cat_val)) {
          # fallback: normalize label and match to normalized category values
          norm_label <- normalize_cat_label(label)
          # unique categories in data
          cats <- unique(subdata[[csv_col]])
          cats_norm <- tolower(trimws(as.character(cats)))
          cats_norm <- gsub("[-–—]+", "-", cats_norm)
          idx <- which(cats_norm == norm_label)
          if (length(idx) == 1) {
            cat_val <- cats[idx]
          } else {
            # fallback no match
            cat_val <- label
          }
        }
        n_cat <- sum(subdata[[csv_col]] == cat_val, na.rm=TRUE)
        n_total <- sum(!is.na(subdata[[csv_col]]))
        val <- format_n_pct(n_cat, n_total)
      }
    } else {
      val <- paste0("TODO: unsupported format_hint '", format_hint, "'")
    }
    output_mat[i, j+1] <- val
  }
}

# Replace any NA in output_mat with empty string
output_mat[is.na(output_mat)] <- ""

# Print function for final table
print_final_table <- function(row_labels, data_mat, treatment_headers) {
  # Combine row labels and data
  df <- as.data.frame(cbind(row_labels, data_mat), stringsAsFactors=FALSE)
  colnames(df) <- c("", treatment_headers)

  # Determine max width per column
  col_widths <- sapply(df, function(col) max(nchar(as.character(col), type="width"), na.rm=TRUE))

  # Print header
  header_line <- paste(mapply(function(x, w) format(x, width=w, justify="left"), names(df), col_widths), collapse="  ")
  cat(header_line, "\n")
  cat(paste(mapply(function(w) paste(rep("-", w), collapse=""), col_widths), collapse="  "), "\n")

  # Print rows
  for (i in seq_len(nrow(df))) {
    row_vals <- df[i, ]
    # For group_header rows, flush left; for data rows, indent first col
    first_col <- row_vals[[1]]
    if (!is.na(first_col) && !startsWith(first_col, "  ") && first_col != "") {
      # group header row
      row_vals[[1]] <- format(first_col, width=col_widths[1], justify="left")
    } else {
      # data row, indent first col
      row_vals[[1]] <- format(first_col, width=col_widths[1], justify="left")
    }
    # Format other columns left justified
    for (j in 2:length(row_vals)) {
      row_vals[[j]] <- format(row_vals[[j]], width=col_widths[j], justify="left")
    }
    line <- paste(row_vals, collapse="  ")
    cat(line, "\n")
  }
  cat("\n")
}

# Print the final table
print_final_table(output_mat[,1], output_mat[, -1, drop=FALSE], treatment_headers)


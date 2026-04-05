library(data.table)
library(stringr)
library(stats)

# Helper functions
normalize_label <- function(x) {
  x <- tolower(x)
  x <- trimws(x)
  x <- gsub("–", "-", x, fixed=TRUE) # normalize dashes
  x
}

format_count <- function(n) {
  if (is.na(n)) return("")
  as.character(n)
}

format_mean_sd <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  m <- mean(x, na.rm=TRUE)
  s <- sd(x, na.rm=TRUE)
  if (is.na(m) || is.na(s)) return("")
  sprintf("%.1f (%.1f)", m, s)
}

format_median <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  med <- median(x, na.rm=TRUE)
  if (is.na(med)) return("")
  if (med == floor(med)) sprintf("%d", med) else sprintf("%.1f", med)
}

format_min_max <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  mn <- min(x, na.rm=TRUE)
  mx <- max(x, na.rm=TRUE)
  if (is.na(mn) || is.na(mx)) return("")
  if (mn == floor(mn) && mx == floor(mx)) {
    sprintf("%d-%d", mn, mx)
  } else {
    sprintf("%.1f-%.1f", mn, mx)
  }
}

format_n_pct <- function(n, total) {
  if (is.na(n) || is.na(total) || total == 0) return("")
  pct <- 100 * n / total
  sprintf("%d (%.1f%%)", n, pct)
}

# Read CSV path from mapped_plan
csv_path <- "data/_adsl+.csv"

# Read data
data <- fread(csv_path, data.table=FALSE)

# Treatment group column
trt_group <- "TRT01A"

# Extract treatment levels
trt_levels <- unique(data[[trt_group]])

# DOCX columns from mapped_plan
docx_columns <- c("Treatment A", "Treatment B")

# Map DOCX columns to actual treatment levels
# Try exact match first
trt_map <- character(length(docx_columns))
for (i in seq_along(docx_columns)) {
  col <- docx_columns[i]
  # Exact match
  if (col %in% trt_levels) {
    trt_map[i] <- col
  } else if (i <= length(trt_levels)) {
    # fallback to position
    trt_map[i] <- trt_levels[i]
  } else {
    trt_map[i] <- NA_character_
  }
}

# Group sizes from mapped_plan (placeholders "nnn" replaced by actual counts)
group_sizes <- sapply(trt_map, function(t) {
  if (is.na(t)) return(NA)
  sum(data[[trt_group]] == t, na.rm=TRUE)
})
names(group_sizes) <- docx_columns

# Build treatment display headers with group sizes
treatment_headers <- mapply(function(col, size) {
  if (is.na(size)) {
    col
  } else {
    sprintf("%s (N=%d)", col, size)
  }
}, docx_columns, group_sizes, USE.NAMES=FALSE)

# Mapping tasks for table 1
mapping_tasks <- list(
  "Age (yr)" = list(
    group_type = "continuous",
    candidate_csv_column = "AGE",
    category_value_map = list()
  ),
  "Age group (yr)" = list(
    group_type = "categorical",
    candidate_csv_column = "AGEGR1",
    category_value_map = list()
  ),
  "Diabetes" = list(
    group_type = "categorical",
    candidate_csv_column = "Diabetes",
    category_value_map = list()
  ),
  "Kidney disease" = list(
    group_type = "categorical",
    candidate_csv_column = "Kidney disease",
    category_value_map = list()
  ),
  "Blood pressure at baseline" = list(
    group_type = "continuous",
    candidate_csv_column = "Blood pressure at baseline",
    category_value_map = list()
  )
)

# Table 1 ordered rows
ordered_rows <- list(
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
  list(kind="data_row", group="Blood pressure at baseline", label="Min-max", format_hint="min_max")
)

# Group info for indentation
group_info <- list(
  "Age (yr)" = list(group_type="continuous", subrows=c("n", "Mean (SD)", "Median", "Min-max")),
  "Age group (yr)" = list(group_type="categorical", subrows=c("n", "18–40", "41–64", "65")),
  "Diabetes" = list(group_type="categorical", subrows=c("n", "Yes", "No")),
  "Kidney disease" = list(group_type="categorical", subrows=c("n", "Stage 1", "Stage 2", "Stage 3")),
  "Blood pressure at baseline" = list(group_type="continuous", subrows=c("n", "Mean (SD)", "Median", "Min-max"))
)

# Normalize function for matching category labels
normalize_cat <- function(x) {
  x <- tolower(x)
  x <- trimws(x)
  x <- gsub("–", "-", x, fixed=TRUE)
  x
}

# Prepare output matrix for table 1
n_rows <- length(ordered_rows)
n_cols <- length(docx_columns) + 1 # +1 for row label
output_mat <- matrix("", nrow=n_rows, ncol=n_cols)
colnames(output_mat) <- c("", docx_columns)

# Fill row labels with indentation
current_group <- NULL
for (i in seq_len(n_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind == "group_header") {
    output_mat[i, 1] <- row$label
    current_group <- row$label
  } else if (row$kind == "data_row") {
    # Indent data rows
    output_mat[i, 1] <- paste0("  ", row$label)
  }
}

# Function to get mapping task by group name
get_mapping_task <- function(group_name) {
  if (group_name %in% names(mapping_tasks)) {
    mapping_tasks[[group_name]]
  } else {
    NULL
  }
}

# Fill data cells
for (i in seq_len(n_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind != "data_row") next
  group_name <- row$group
  label <- row$label
  format_hint <- row$format_hint
  mt <- get_mapping_task(group_name)
  if (is.null(mt)) {
    # TODO: mapping task missing for this group
    next
  }
  csv_col <- mt$candidate_csv_column
  group_type <- mt$group_type
  cat_map <- mt$category_value_map

  # For each treatment column
  for (j in seq_along(docx_columns)) {
    trt_label <- docx_columns[j]
    trt_val <- trt_map[j]
    if (is.na(trt_val)) {
      # No matching treatment level
      output_mat[i, j+1] <- ""
      next
    }
    # Subset data for this treatment
    subdata <- data[data[[trt_group]] == trt_val, , drop=FALSE]

    # Compute value based on format_hint and group_type
    val <- ""
    if (format_hint == "count") {
      if (label == "n") {
        # Count of non-missing in candidate column
        if (group_type == "continuous") {
          val <- sum(!is.na(subdata[[csv_col]]))
        } else if (group_type == "categorical") {
          val <- nrow(subdata)
        } else {
          val <- sum(!is.na(subdata[[csv_col]]))
        }
        val <- format_count(val)
      } else {
        # TODO: count for other labels?
        val <- ""
      }
    } else if (format_hint == "mean_sd") {
      if (group_type == "continuous") {
        val <- format_mean_sd(subdata[[csv_col]])
      } else {
        # TODO: mean_sd for non-continuous?
        val <- ""
      }
    } else if (format_hint == "median") {
      if (group_type == "continuous") {
        val <- format_median(subdata[[csv_col]])
      } else {
        # TODO: median for non-continuous?
        val <- ""
      }
    } else if (format_hint == "min_max") {
      if (group_type == "continuous") {
        val <- format_min_max(subdata[[csv_col]])
      } else {
        # TODO: min_max for non-continuous?
        val <- ""
      }
    } else if (format_hint == "n_pct") {
      # For categorical subgroups
      # label is category label
      # Map label to category value if available
      cat_val <- NULL
      if (length(cat_map) > 0) {
        # Try exact match
        if (label %in% names(cat_map)) {
          cat_val <- cat_map[[label]]
        } else {
          # fallback normalized matching
          norm_label <- normalize_label(label)
          nm <- sapply(names(cat_map), normalize_label)
          idx <- which(nm == norm_label)
          if (length(idx) == 1) {
            cat_val <- cat_map[[names(cat_map)[idx]]]
          }
        }
      }
      if (is.null(cat_val)) {
        # fallback: try normalized matching to raw data
        norm_label <- normalize_label(label)
        vals <- unique(subdata[[csv_col]])
        norm_vals <- tolower(trimws(as.character(vals)))
        norm_vals <- gsub("–", "-", norm_vals, fixed=TRUE)
        idx <- which(norm_vals == norm_label)
        if (length(idx) == 1) {
          cat_val <- vals[idx]
        } else {
          # TODO: category value mapping missing or ambiguous
          cat_val <- label # fallback to label itself
        }
      }
      # Count of subjects in category
      n_cat <- sum(subdata[[csv_col]] == cat_val, na.rm=TRUE)
      total_n <- nrow(subdata)
      val <- format_n_pct(n_cat, total_n)
    } else {
      # TODO: unknown format_hint
      val <- ""
    }
    output_mat[i, j+1] <- val
  }
}

# Replace NA with empty string
output_mat[is.na(output_mat)] <- ""

# Print table with indentation and no row names
print_table <- function(mat) {
  # Determine max width for first column
  first_col <- mat[,1]
  max_first_col_width <- max(nchar(first_col), na.rm=TRUE)

  # Determine max width for each treatment column
  n_cols <- ncol(mat)
  max_col_widths <- integer(n_cols)
  for (j in 1:n_cols) {
    max_col_widths[j] <- max(nchar(mat[,j], keepNA=FALSE), nchar(colnames(mat)[j]), na.rm=TRUE)
  }

  # Print header
  header_line <- paste0(
    format(colnames(mat)[1], width=max_col_widths[1], justify="left"), "  ",
    paste(sapply(2:n_cols, function(j) format(treatment_headers[j-1], width=max_col_widths[j], justify="centre")), collapse="  ")
  )
  cat(header_line, "\n")

  # Print rows
  for (i in 1:nrow(mat)) {
    row_label <- mat[i,1]
    # Determine if group header (no indent) or data row (indent)
    indent <- ifelse(substr(row_label, 1, 2) == "  ", "  ", "")
    label_text <- trimws(row_label)
    label_print <- paste0(indent, format(label_text, width=max_col_widths[1] - nchar(indent), justify="left"))
    row_vals <- sapply(2:n_cols, function(j) format(mat[i,j], width=max_col_widths[j], justify="centre"))
    line <- paste(c(label_print, row_vals), collapse="  ")
    cat(line, "\n")
  }
  cat("\n")
}

# Print the single table
print_table(output_mat)

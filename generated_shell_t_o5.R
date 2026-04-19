library(data.table)

# Helper functions
normalize_label <- function(x) {
  x <- tolower(trimws(x))
  x <- gsub("–", "-", x, fixed = TRUE) # normalize hyphen
  x
}

format_count <- function(x) {
  as.character(x)
}

format_mean_sd <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  m <- mean(x, na.rm = TRUE)
  s <- sd(x, na.rm = TRUE)
  if (is.na(m) || is.na(s)) return("")
  sprintf("%.1f (%.1f)", m, s)
}

format_mean <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  m <- median(x, na.rm = TRUE)
  if (is.na(m)) return("")
  sprintf("%.1f", m)
}

format_min_max <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("")
  mn <- min(x, na.rm = TRUE)
  mx <- max(x, na.rm = TRUE)
  if (is.na(mn) || is.na(mx)) return("")
  sprintf("%.0f–%.0f", mn, mx) # en dash
}

format_n_pct <- function(n, total) {
  if (total == 0) return("")
  p <- 100 * n / total
  sprintf("%d (%.0f%%)", n, p)
}

# Read CSV
csv_path <- "data/adsl.csv"
data <- fread(csv_path, data.table = FALSE)

# Treatment grouping
trt_group <- "TRT01A"

# Extract unique treatment levels
trt_levels <- unique(data[[trt_group]])

# DOCX columns and group sizes
docx_columns <- c("Treatment A", "Treatment B")
group_sizes <- c("Treatment A" = NA, "Treatment B" = NA) # "nnn" placeholder, unknown numeric

# Map DOCX columns to actual treatment levels
# Try exact match first
map_docx_to_trt <- rep(NA_character_, length(docx_columns))
for (i in seq_along(docx_columns)) {
  col <- docx_columns[i]
  if (col %in% trt_levels) {
    map_docx_to_trt[i] <- col
  }
}
# Fallback to position mapping for unmatched
for (i in seq_along(map_docx_to_trt)) {
  if (is.na(map_docx_to_trt[i]) && i <= length(trt_levels)) {
    map_docx_to_trt[i] <- trt_levels[i]
  }
}

# Prepare treatment display headers with group sizes if known
# group_sizes are "nnn" placeholders, so omit N counts
treatment_headers <- docx_columns

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
    category_value_map = list(
      "18–40" = "1",
      "41–64" = "2",
      "≥65" = "3"
    )
  ),
  "Sex" = list(
    group_type = "categorical",
    candidate_csv_column = "SEX",
    category_value_map = list(
      "Male" = "M",
      "Female" = "F"
    )
  ),
  "Ethnicity" = list(
    group_type = "categorical",
    candidate_csv_column = "ETHNIC",
    category_value_map = list(
      "Hispanic or Latino" = "Hispanic or Latino",
      "Not Hispanic or Latino" = "Not Hispanic or Latino"
    )
  ),
  "Race" = list(
    group_type = "categorical",
    candidate_csv_column = "RACE",
    category_value_map = list(
      "American Indian or Alaska Native" = "American Indian or Alaska Native",
      "Asian" = "Asian",
      "Black or African American" = "Black or African American",
      "Native Hawaiian or other Pacific Islander" = "Native Hawaiian or other Pacific Islander",
      "White" = "White"
    )
  )
)

# Table 1 ordered rows and group info
ordered_rows <- list(
  list(kind = "group_header", label = "Age (yr)"),
  list(kind = "data_row", group = "Age (yr)", label = "n", format_hint = "count"),
  list(kind = "data_row", group = "Age (yr)", label = "Mean (SD)", format_hint = "mean_sd"),
  list(kind = "data_row", group = "Age (yr)", label = "Median", format_hint = "mean"),
  list(kind = "data_row", group = "Age (yr)", label = "Min–max", format_hint = "min_max"),
  list(kind = "group_header", label = "Age group (yr)"),
  list(kind = "data_row", group = "Age group (yr)", label = "n", format_hint = "count"),
  list(kind = "data_row", group = "Age group (yr)", label = "18–40", format_hint = "n_pct"),
  list(kind = "data_row", group = "Age group (yr)", label = "41–64", format_hint = "n_pct"),
  list(kind = "data_row", group = "Age group (yr)", label = "≥65", format_hint = "n_pct"),
  list(kind = "group_header", label = "Sex"),
  list(kind = "data_row", group = "Sex", label = "n", format_hint = "count"),
  list(kind = "data_row", group = "Sex", label = "Male", format_hint = "n_pct"),
  list(kind = "data_row", group = "Sex", label = "Female", format_hint = "n_pct"),
  list(kind = "group_header", label = "Ethnicity"),
  list(kind = "data_row", group = "Ethnicity", label = "n", format_hint = "count"),
  list(kind = "data_row", group = "Ethnicity", label = "Hispanic or Latino", format_hint = "n_pct"),
  list(kind = "data_row", group = "Ethnicity", label = "Not Hispanic or Latino", format_hint = "n_pct"),
  list(kind = "group_header", label = "Race"),
  list(kind = "data_row", group = "Race", label = "n", format_hint = "count"),
  list(kind = "data_row", group = "Race", label = "American Indian or Alaska Native", format_hint = "n_pct"),
  list(kind = "data_row", group = "Race", label = "Asian", format_hint = "n_pct"),
  list(kind = "data_row", group = "Race", label = "Black or African American", format_hint = "n_pct"),
  list(kind = "data_row", group = "Race", label = "Native Hawaiian or other Pacific Islander", format_hint = "n_pct"),
  list(kind = "data_row", group = "Race", label = "White", format_hint = "n_pct")
)

group_info <- list(
  "Age (yr)" = list(group_type = "continuous", subrows = c("n", "Mean (SD)", "Median", "Min–max")),
  "Age group (yr)" = list(group_type = "categorical", subrows = c("n", "18–40", "41–64", "≥65")),
  "Sex" = list(group_type = "categorical", subrows = c("n", "Male", "Female")),
  "Ethnicity" = list(group_type = "categorical", subrows = c("n", "Hispanic or Latino", "Not Hispanic or Latino")),
  "Race" = list(group_type = "categorical", subrows = c("n", "American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or other Pacific Islander", "White"))
)

# Normalize function for matching category labels
normalize_cat <- function(x) {
  x <- tolower(trimws(x))
  x <- gsub("–", "-", x, fixed = TRUE)
  x
}

# Prepare output matrix for the table
n_rows <- length(ordered_rows)
n_cols <- length(docx_columns) + 1 # plus label column
output_mat <- matrix("", nrow = n_rows, ncol = n_cols)

# Fill label column with row labels
for (i in seq_len(n_rows)) {
  output_mat[i, 1] <- ordered_rows[[i]]$label
}

# Indentation for child rows
indent <- "  "
for (i in seq_len(n_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind == "data_row") {
    output_mat[i, 1] <- paste0(indent, output_mat[i, 1])
  }
}

# Function to get counts and stats for continuous group
get_continuous_stats <- function(x) {
  list(
    n = sum(!is.na(x)),
    mean_sd = format_mean_sd(x),
    median = format_mean(x),
    min_max = format_min_max(x)
  )
}

# Function to get counts and percentages for categorical group
get_categorical_stats <- function(x, categories, cat_map) {
  # x is vector of raw CSV values
  # categories is vector of DOCX labels
  # cat_map maps DOCX label to CSV value
  n_total <- sum(!is.na(x))
  n_counts <- integer(length(categories))
  names(n_counts) <- categories
  for (cat in categories) {
    val <- cat_map[[cat]]
    if (is.null(val)) {
      # fallback: try normalized matching
      norm_cat <- normalize_cat(cat)
      matches <- which(normalize_cat(unique(x)) == norm_cat)
      if (length(matches) == 1) {
        val <- unique(x)[matches]
      } else {
        val <- NA
      }
    }
    if (!is.na(val)) {
      n_counts[cat] <- sum(x == val, na.rm = TRUE)
    } else {
      n_counts[cat] <- NA
    }
  }
  n_counts["n"] <- n_total
  n_counts
}

# Fill data cells
for (i in seq_len(n_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind == "data_row") {
    group_name <- row$group
    label <- row$label
    format_hint <- row$format_hint
    task <- mapping_tasks[[group_name]]
    if (is.null(task)) {
      # TODO: mapping task missing for this group
      next
    }
    csv_col <- task$candidate_csv_column
    cat_map <- task$category_value_map
    group_type <- task$group_type

    # For each DOCX column, map to treatment level and filter data
    for (j in seq_along(docx_columns)) {
      trt_val <- map_docx_to_trt[j]
      if (is.na(trt_val)) {
        # TODO: treatment mapping missing
        output_mat[i, j + 1] <- ""
        next
      }
      subdata <- data[data[[trt_group]] == trt_val, , drop = FALSE]
      x <- subdata[[csv_col]]

      if (group_type == "continuous") {
        stats <- get_continuous_stats(x)
        val <- switch(format_hint,
                      count = as.character(stats$n),
                      mean_sd = stats$mean_sd,
                      mean = stats$median,
                      min_max = stats$min_max,
                      "")
        output_mat[i, j + 1] <- ifelse(is.na(val), "", val)
      } else if (group_type == "categorical") {
        # For categorical, label "n" means total count
        if (label == "n") {
          n_val <- sum(!is.na(x))
          output_mat[i, j + 1] <- as.character(n_val)
        } else {
          # For category rows, get count and percent
          cat_val <- cat_map[[label]]
          if (is.null(cat_val)) {
            # fallback normalized matching
            norm_label <- normalize_cat(label)
            unique_vals <- unique(x)
            matches <- which(normalize_cat(unique_vals) == norm_label)
            if (length(matches) == 1) {
              cat_val <- unique_vals[matches]
            } else {
              # TODO: category mapping missing
              output_mat[i, j + 1] <- ""
              next
            }
          }
          n_cat <- sum(x == cat_val, na.rm = TRUE)
          n_total <- sum(!is.na(x))
          val <- format_n_pct(n_cat, n_total)
          output_mat[i, j + 1] <- val
        }
      } else {
        # TODO: unknown group type
        output_mat[i, j + 1] <- ""
      }
    }
  } else if (row$kind == "group_header") {
    # group header row: blank data cells
    output_mat[i, 2:(n_cols)] <- ""
  }
}

# Replace any NA in output_mat with empty string
output_mat[is.na(output_mat)] <- ""

# Prepare to print table
# Column widths
col_widths <- integer(n_cols)
for (j in seq_len(n_cols)) {
  max_len <- max(nchar(output_mat[, j], type = "width"), na.rm = TRUE)
  col_widths[j] <- max(max_len, nchar(if (j == 1) "" else treatment_headers[j - 1], type = "width"))
}

# Prepare header row
header_row <- character(n_cols)
header_row[1] <- ""
for (j in 2:n_cols) {
  header_row[j] <- treatment_headers[j - 1]
}

# Print function for aligned table
print_table <- function(mat, header, widths) {
  # Print header
  cat(sprintf("%-*s", widths[1], header[1]))
  for (j in 2:length(header)) {
    cat("  ", sprintf(paste0("%-", widths[j], "s"), header[j]), sep = "")
  }
  cat("\n")
  # Print rows
  for (i in seq_len(nrow(mat))) {
    cat(sprintf("%-*s", widths[1], mat[i, 1]))
    for (j in 2:ncol(mat)) {
      cat("  ", sprintf(paste0("%-", widths[j], "s"), mat[i, j]), sep = "")
    }
    cat("\n")
  }
}

# Print the final table
print_table(output_mat, header_row, col_widths)

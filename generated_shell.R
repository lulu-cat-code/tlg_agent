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
  if (is.numeric(med)) sprintf("%.1f", med) else as.character(med)
}

format_min_max <- function(x) {
  if (length(x) == 0) return("")
  mn <- min(x, na.rm=TRUE)
  mx <- max(x, na.rm=TRUE)
  if (is.na(mn) || is.na(mx)) return("")
  sprintf("%.1f–%.1f", mn, mx)
}

format_n_pct <- function(n, total) {
  if (total == 0) return("")
  pct <- 100 * n / total
  sprintf("%d (%.1f%%)", n, pct)
}

# Read mapped_plan from environment (assumed to be loaded externally)
# For this script, we assume mapped_plan is available as a variable

# Extract CSV path
csv_path <- "data/_adsl++.csv"

# Read data
data <- fread(csv_path, data.table=FALSE)

# Treatment group column
trt_group <- "TRT01A"

# Extract tables and mapping_tasks from mapped_plan
# For this script, we materialize minimal constants from input

# Table 1 info
columns_docx <- c("Treatment A", "Treatment B")
group_sizes <- list("Treatment A" = NA, "Treatment B" = NA) # 'nnn' placeholder, no numeric size

ordered_rows <- list(
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
  list(kind="data_row", group="Race", label="White", format_hint="n_pct"),
  list(kind="group_header", label="Weight (kg) at baseline"),
  list(kind="data_row", group="Weight (kg) at baseline", label="n", format_hint="count"),
  list(kind="data_row", group="Weight (kg) at baseline", label="Mean (SD)", format_hint="mean_sd"),
  list(kind="data_row", group="Weight (kg) at baseline", label="Median", format_hint="median"),
  list(kind="data_row", group="Weight (kg) at baseline", label="Min–max", format_hint="min_max"),
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

# Mapping tasks minimal info
mapping_tasks <- list(
  list(group_name="Age (yr)", group_type="continuous", candidate_csv_column="AGE", category_value_map=list()),
  list(group_name="Age group (yr)", group_type="categorical", candidate_csv_column="AGEGR1", category_value_map=list()),
  list(group_name="Sex", group_type="categorical", candidate_csv_column="SEX", category_value_map=list()),
  list(group_name="Ethnicity", group_type="categorical", candidate_csv_column="ETHNIC", category_value_map=list()),
  list(group_name="Race", group_type="categorical", candidate_csv_column="RACE", category_value_map=list()),
  list(group_name="Weight (kg) at baseline", group_type="continuous", candidate_csv_column="baseline_weight", category_value_map=list()),
  list(group_name="Diabetes", group_type="categorical", candidate_csv_column="Diabetes", category_value_map=list()),
  list(group_name="Kidney disease", group_type="categorical", candidate_csv_column="Disease_kidney", category_value_map=list()),
  list(group_name="Blood pressure at baseline", group_type="continuous", candidate_csv_column="baseline_bp", category_value_map=list())
)

# Normalize function for matching category labels
normalize_cat <- function(x) {
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

# Treatment levels
trt_levels <- unique(data[[trt_group]])

# Map DOCX columns to treatment levels
map_docx_to_trt <- function(docx_cols, trt_lvls) {
  # Try exact match
  matched <- sapply(docx_cols, function(dc) {
    idx <- which(trt_lvls == dc)
    if (length(idx) == 1) return(trt_lvls[idx]) else NA_character_
  })
  # For NA, fallback to position
  for (i in seq_along(matched)) {
    if (is.na(matched[i]) && i <= length(trt_lvls)) {
      matched[i] <- trt_lvls[i]
    }
  }
  matched
}

trt_map <- map_docx_to_trt(columns_docx, trt_levels)

# Compute group sizes if possible
group_sizes_num <- sapply(trt_map, function(trt) {
  if (is.na(trt)) return(NA_integer_)
  sum(data[[trt_group]] == trt, na.rm=TRUE)
})

# Build treatment display headers
treatment_headers <- mapply(function(col, size) {
  if (is.na(size)) {
    col
  } else {
    sprintf("%s (N=%d)", col, size)
  }
}, columns_docx, group_sizes_num, USE.NAMES=FALSE)

# Prepare output table container
output_table <- matrix("", nrow=length(ordered_rows), ncol=length(columns_docx)+1)
colnames(output_table) <- c("", treatment_headers)

# Fill row labels with indentation for data rows
for (i in seq_along(ordered_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind == "group_header") {
    output_table[i, 1] <- row$label
  } else if (row$kind == "data_row") {
    output_table[i, 1] <- paste0("  ", row$label)
  }
}

# Helper to get mapping task for a group
get_mapping_for_group <- function(group_name) {
  mt <- find_mapping_task(group_name)
  if (is.null(mt)) stop(paste("No mapping task for group", group_name))
  mt
}

# Helper to get subset data for a treatment
get_trt_data <- function(trt_val) {
  subset(data, data[[trt_group]] == trt_val)
}

# Helper to get counts and stats for continuous
compute_continuous_stats <- function(x, label) {
  switch(label,
         "n" = format_count(sum(!is.na(x))),
         "Mean (SD)" = format_mean_sd(x),
         "Median" = format_median(x),
         "Min–max" = format_min_max(x),
         "" # fallback empty
  )
}

# Helper to compute counts and percentages for categorical
compute_categorical_stats <- function(x, label, total) {
  if (label == "n") {
    format_count(sum(!is.na(x)))
  } else {
    # Try to match label to category
    norm_label <- normalize_cat(label)
    # Try exact match
    matched_vals <- x[normalize_cat(x) == norm_label]
    n <- length(matched_vals)
    if (n == 0) {
      # fallback: try partial match or TODO
      # TODO: no matching category found for label
      n <- 0
    }
    format_n_pct(n, total)
  }
}

# Fill data cells
for (i in seq_along(ordered_rows)) {
  row <- ordered_rows[[i]]
  if (row$kind == "data_row") {
    group_name <- row$group
    label <- row$label
    format_hint <- row$format_hint
    mt <- get_mapping_for_group(group_name)
    csv_col <- mt$candidate_csv_column
    group_type <- mt$group_type
    cat_map <- mt$category_value_map

    for (j in seq_along(trt_map)) {
      trt_val <- trt_map[j]
      if (is.na(trt_val)) {
        output_table[i, j+1] <- "" # no treatment mapping
        next
      }
      subdata <- get_trt_data(trt_val)
      if (group_type == "continuous") {
        x <- subdata[[csv_col]]
        val <- compute_continuous_stats(x, label)
        output_table[i, j+1] <- val
      } else if (group_type == "categorical") {
        x <- subdata[[csv_col]]
        total_n <- sum(!is.na(x))
        if (label == "n") {
          val <- format_count(total_n)
          output_table[i, j+1] <- val
        } else {
          # Use category_value_map if available
          cat_val <- NULL
          if (length(cat_map) > 0 && label %in% names(cat_map)) {
            cat_val <- cat_map[[label]]
          }
          if (!is.null(cat_val)) {
            n <- sum(x == cat_val, na.rm=TRUE)
            val <- format_n_pct(n, total_n)
            output_table[i, j+1] <- val
          } else {
            # fallback: match normalized label
            norm_label <- normalize_cat(label)
            n <- sum(normalize_cat(as.character(x)) == norm_label, na.rm=TRUE)
            if (n == 0) {
              # TODO: no matching category found for label
              val <- ""
            } else {
              val <- format_n_pct(n, total_n)
            }
            output_table[i, j+1] <- val
          }
        }
      } else {
        # TODO: unknown group_type
        output_table[i, j+1] <- ""
      }
    }
  }
}

# Replace NA with empty string
output_table[is.na(output_table)] <- ""

# Print tables with indentation and no row names
print_table <- function(mat) {
  # Determine max width for first column
  first_col_width <- max(nchar(mat[,1], type = "width"), na.rm=TRUE)
  # Determine max width for each treatment column
  col_widths <- sapply(2:ncol(mat), function(j) max(nchar(mat[,j], type = "width"), na.rm=TRUE))

  # Print header
  header_line <- paste0(
    format(mat[1,1], width=first_col_width, justify="left"), "  ",
    paste(mapply(function(h, w) format(h, width=w, justify="right"), mat[1,-1], col_widths), collapse="  ")
  )
  cat(header_line, "\n")

  # Print rows
  for (i in 2:nrow(mat)) {
    label <- mat[i,1]
    # Determine if group header (no indent) or data row (indent)
    indent <- ifelse(substr(label, 1, 2) == "  ", "  ", "")
    label_print <- format(label, width=first_col_width, justify="left")
    if (indent != "") {
      label_print <- paste0(indent, trimws(label_print))
      label_print <- format(label_print, width=first_col_width, justify="left")
    }
    row_vals <- mapply(function(x, w) format(x, width=w, justify="right"), mat[i,-1], col_widths)
    cat(label_print, "  ", paste(row_vals, collapse="  "), "\n")
  }
  cat("\n")
}

# Print the single table
print_table(output_table)

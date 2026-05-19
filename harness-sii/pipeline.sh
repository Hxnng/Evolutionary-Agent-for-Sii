#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Unified evaluation pipeline (SimpleVQA / 2Wiki / benchmark)
# Edit this block or export env vars before running.
###############################################################################

DATASET_NAME="${DATASET_NAME:-simplevqa}"   # simplevqa | 2wiki | benchmark | all
PYTHON_BIN="${PYTHON_BIN:-python}"
LIMIT="${LIMIT:-200}"
OFFSET="${OFFSET:-0}"
WORKERS="${WORKERS:-8}"

RUN_BASELINE="${RUN_BASELINE:-1}"
RUN_EVOLVED="${RUN_EVOLVED:-1}"

OUTPUT_ROOT="${OUTPUT_ROOT:-runs/pipeline}"
RUN_NAME="${RUN_NAME:-submission}"

MODEL_NAME="${MODEL_NAME:-}"
LLM_URL="${LLM_URL:-}"

SIMPLEVQA_DATASET="${SIMPLEVQA_DATASET:-data/simpleVQA/simpleVQA_final_modified.json}"
SIMPLEVQA_IMAGE_ROOT="${SIMPLEVQA_IMAGE_ROOT:-data/simpleVQA/simpleVQA_datasets}"

TWOWIKI_DATASET="${TWOWIKI_DATASET:-data/2wiki}"
TWOWIKI_SPLIT="${TWOWIKI_SPLIT:-validation}"
TWOWIKI_MAX_CONTEXT_CHARS="${TWOWIKI_MAX_CONTEXT_CHARS:-12000}"
TWOWIKI_MAX_SENTENCES_PER_TITLE="${TWOWIKI_MAX_SENTENCES_PER_TITLE:-}"
TWOWIKI_STRICT="${TWOWIKI_STRICT:-0}"

BENCHMARK_DATASET="${BENCHMARK_DATASET:-data/benchmark.csv}"
BENCHMARK_IMAGE_ROOT="${BENCHMARK_IMAGE_ROOT:-}"

METRICS_CASE_LIMIT="${METRICS_CASE_LIMIT:-$LIMIT}"

###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() { printf '[pipeline] %s\n' "$*"; }
die() { printf '[pipeline][error] %s\n' "$*" >&2; exit 1; }

append_optional_llm_args() {
  local -n out_args=$1
  if [[ -n "$MODEL_NAME" ]]; then
    out_args+=(--model "$MODEL_NAME")
  fi
  if [[ -n "$LLM_URL" ]]; then
    out_args+=(--llm-url "$LLM_URL")
  fi
}

run_simplevqa() {
  local mode="$1"
  local mode_flag=()
  [[ "$mode" == "baseline" ]] && mode_flag+=(--baseline)

  local out_dir="$OUTPUT_ROOT/simplevqa/$mode"
  local pred="$out_dir/predictions_${LIMIT}.jsonl"
  local traj="$out_dir/trajectories_${LIMIT}"
  local metrics="$out_dir/metrics_${LIMIT}.json"
  local args=(
    -B evaluate.py
    --dataset "$SIMPLEVQA_DATASET"
    --image-root "$SIMPLEVQA_IMAGE_ROOT"
    --output "$pred"
    --traj-dir "$traj"
    --metrics-output "$metrics"
    --split-name "simplevqa_${mode}"
    --limit "$LIMIT"
    --offset "$OFFSET"
    --workers "$WORKERS"
  )
  append_optional_llm_args args
  log "SimpleVQA $mode workers=$WORKERS -> $pred"
  "$PYTHON_BIN" "${args[@]}" "${mode_flag[@]}"
}

run_2wiki() {
  local mode="$1"
  local mode_flag=()
  [[ "$mode" == "baseline" ]] && mode_flag+=(--baseline)
  [[ "$TWOWIKI_STRICT" == "1" ]] && mode_flag+=(--strict)
  if [[ -n "$TWOWIKI_MAX_SENTENCES_PER_TITLE" ]]; then
    mode_flag+=(--max-sentences-per-title "$TWOWIKI_MAX_SENTENCES_PER_TITLE")
  fi

  local out_dir="$OUTPUT_ROOT/2wiki/$mode"
  local pred="$out_dir/predictions_${LIMIT}.jsonl"
  local traj="$out_dir/trajectories_${LIMIT}"
  local metrics="$out_dir/metrics_${LIMIT}.json"
  local args=(
    -B evaluate_2wiki.py
    --dataset "$TWOWIKI_DATASET"
    --split "$TWOWIKI_SPLIT"
    --output "$pred"
    --traj-dir "$traj"
    --metrics-output "$metrics"
    --split-name "2wiki_${mode}"
    --limit "$LIMIT"
    --offset "$OFFSET"
    --max-context-chars "$TWOWIKI_MAX_CONTEXT_CHARS"
    --workers "$WORKERS"
  )
  append_optional_llm_args args
  log "2Wiki $mode workers=$WORKERS -> $pred"
  "$PYTHON_BIN" "${args[@]}" "${mode_flag[@]}"
}

run_benchmark() {
  local mode="$1"
  local mode_flag=()
  [[ "$mode" == "baseline" ]] && mode_flag+=(--baseline)
  if [[ -n "$BENCHMARK_IMAGE_ROOT" ]]; then
    mode_flag+=(--image-root "$BENCHMARK_IMAGE_ROOT")
  fi

  local out_dir="$OUTPUT_ROOT/benchmark/$mode"
  local pred="$out_dir/predictions_${LIMIT}.jsonl"
  local traj="$out_dir/trajectories_${LIMIT}"
  local metrics="$out_dir/metrics_${LIMIT}.json"
  local args=(
    -B evaluate_benchmark.py
    --dataset "$BENCHMARK_DATASET"
    --output "$pred"
    --traj-dir "$traj"
    --metrics-output "$metrics"
    --split-name "benchmark_${mode}"
    --limit "$LIMIT"
    --offset "$OFFSET"
    --workers "$WORKERS"
  )
  append_optional_llm_args args
  log "benchmark $mode workers=$WORKERS -> $pred"
  "$PYTHON_BIN" "${args[@]}" "${mode_flag[@]}"
}

pred_path() {
  printf '%s/%s/%s/predictions_%s.jsonl' "$OUTPUT_ROOT" "$1" "$2" "$LIMIT"
}

traj_path() {
  printf '%s/%s/%s/trajectories_%s' "$OUTPUT_ROOT" "$1" "$2" "$LIMIT"
}

run_metrics() {
  local dataset="$1"
  local report="$OUTPUT_ROOT/$dataset/metris_report_${LIMIT}.json"
  mkdir -p "$OUTPUT_ROOT/$dataset"
  if [[ "$RUN_BASELINE" == "1" && "$RUN_EVOLVED" == "1" ]]; then
    log "metrics compare -> $report"
    "$PYTHON_BIN" -B metris.py \
      --baseline-pred "$(pred_path "$dataset" baseline)" \
      --baseline-traj "$(traj_path "$dataset" baseline)" \
      --evolved-pred "$(pred_path "$dataset" evolved)" \
      --evolved-traj "$(traj_path "$dataset" evolved)" \
      --case-limit "$METRICS_CASE_LIMIT" \
      --name "$RUN_NAME" \
      --output "$report"
  elif [[ "$RUN_EVOLVED" == "1" ]]; then
    "$PYTHON_BIN" -B metris.py \
      --pred "$(pred_path "$dataset" evolved)" \
      --traj-dir "$(traj_path "$dataset" evolved)" \
      --case-limit "$METRICS_CASE_LIMIT" \
      --name "$RUN_NAME" \
      --output "$report"
  elif [[ "$RUN_BASELINE" == "1" ]]; then
    "$PYTHON_BIN" -B metris.py \
      --pred "$(pred_path "$dataset" baseline)" \
      --traj-dir "$(traj_path "$dataset" baseline)" \
      --case-limit "$METRICS_CASE_LIMIT" \
      --name "$RUN_NAME" \
      --output "$report"
  else
    die "Both RUN_BASELINE and RUN_EVOLVED are 0."
  fi
}

run_dataset_suite() {
  local key="$1"
  local runner="$2"
  if [[ "$RUN_BASELINE" == "1" ]]; then
    "$runner" baseline
  fi
  if [[ "$RUN_EVOLVED" == "1" ]]; then
    "$runner" evolved
  fi
  run_metrics "$key"
}

case "$DATASET_NAME" in
  simplevqa|SimpleVQA|simpleVQA)
    run_dataset_suite simplevqa run_simplevqa
    ;;
  2wiki|2Wiki|2WikiMultihopQA|twowiki)
    run_dataset_suite 2wiki run_2wiki
    ;;
  benchmark|Benchmark|bench)
    run_dataset_suite benchmark run_benchmark
    ;;
  all)
    run_dataset_suite simplevqa run_simplevqa
    run_dataset_suite 2wiki run_2wiki
    run_dataset_suite benchmark run_benchmark
    ;;
  *)
    die "Unknown DATASET_NAME=$DATASET_NAME (use simplevqa, 2wiki, benchmark, all)"
    ;;
esac

log "Done."

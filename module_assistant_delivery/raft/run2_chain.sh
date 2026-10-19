#!/usr/bin/env bash
# RAFT run 2 on the GPU in gentle mode (owner's request, 2026-10-19): about half GPU load, the trainer pauses at
# 76 C until 70 C, and a watchdog stops the running job outright if the GPU ever reaches 79 C (owner's hard limit).
# The reference answers (base model, run 1 adapter) were produced before; this trains two configurations, each
# followed by its answers on the hand-written validation set. Private Ollama must be stopped (same GPU).
#   bash raft/run2_chain.sh > run2.log 2>&1        (from module_assistant_delivery/)
cd "$(dirname "$0")/.."
export HF_HUB_OFFLINE=1 PYTHONIOENCODING=utf-8
PY=.venv-raft/Scripts/python.exe
BASE=unsloth/Qwen2.5-7B-Instruct-bnb-4bit
DUTY=${DUTY:-0.5}
LIMIT_C=79
PIDFILE=$(mktemp)
step() { echo "=== $(date '+%H:%M:%S') $*"; }
run() { "$@" & echo $! > "$PIDFILE"; wait $!; }

watchdog() {
  while sleep 5; do
    t=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '\r ')
    if [ -n "$t" ] && [ "$t" -ge "$LIMIT_C" ]; then
      echo "=== WATCHDOG $(date '+%H:%M:%S'): GPU at ${t} C (limit ${LIMIT_C} C): stopping the running job"
      kill "$(cat "$PIDFILE")" 2>/dev/null
      touch "$PIDFILE.stopped"
    fi
  done
}
watchdog & WATCHDOG_PID=$!
trap 'kill $WATCHDOG_PID 2>/dev/null' EXIT
stopped() { [ -e "$PIDFILE.stopped" ]; }

step "train run 2a: v2 data, 1 epoch, LoRA rank 16, lr 2e-4 (duty $DUTY)"
run $PY raft/train.py --model $BASE --run qwen2.5-7b-raft2a --data generated_v2 --epochs 1 --rank 16 --lr 2e-4 --duty $DUTY || echo "FAILED train 2a"
stopped && { step "chain stopped by the temperature watchdog"; exit 1; }
step "answers: run 2a"
run $PY raft/generate_answers.py --label run2a --adapter raft/outputs/qwen2.5-7b-raft2a/adapter --duty $DUTY || echo "FAILED run2a answers"
stopped && { step "chain stopped by the temperature watchdog"; exit 1; }

step "train run 2b: v2 data, 1 epoch, LoRA rank 8, lr 1e-4 (duty $DUTY)"
run $PY raft/train.py --model $BASE --run qwen2.5-7b-raft2b --data generated_v2 --epochs 1 --rank 8 --lr 1e-4 --duty $DUTY || echo "FAILED train 2b"
stopped && { step "chain stopped by the temperature watchdog"; exit 1; }
step "answers: run 2b"
run $PY raft/generate_answers.py --label run2b --adapter raft/outputs/qwen2.5-7b-raft2b/adapter --duty $DUTY || echo "FAILED run2b answers"
step "chain finished"

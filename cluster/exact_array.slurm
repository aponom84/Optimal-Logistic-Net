#!/bin/bash
# SLURM array driver for the exact-solve study on cHARISMa (rocky queue).
#
# Submit with an explicit array range and concurrency cap, e.g. for a 20-row
# manifest running at most 10 at once:
#
#   sbatch --array=1-20%10 cluster/exact_array.slurm cluster/manifest.csv Results/Exact
#
# $1 = manifest csv   $2 = output dir (default Results/Exact)
#
#SBATCH --job-name=olnet_exact
#SBATCH --partition=rocky
#SBATCH --account=proj_1902
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=cluster/logs/%A_%a.out

set -euo pipefail

MANIFEST="${1:-cluster/manifest.csv}"
OUTDIR="${2:-Results/Exact}"

module load Python/Anaconda 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate olnet

cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

echo "host=$(hostname) task=${SLURM_ARRAY_TASK_ID} cpus=${SLURM_CPUS_PER_TASK} manifest=${MANIFEST}"
python cluster/run_one.py --manifest "$MANIFEST" --idx "$SLURM_ARRAY_TASK_ID" --out-dir "$OUTDIR"

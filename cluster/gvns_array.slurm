#!/bin/bash
# SLURM array driver for the multi-seed GVNS runs on cHARISMa (rocky queue).
#
#   sbatch --array=1-N%K cluster/gvns_array.slurm cluster/gvns_manifest.csv Results/GVNS
#
# $1 = manifest csv   $2 = output dir (default Results/GVNS)
#
#SBATCH --job-name=olnet_gvns
#SBATCH --partition=rocky
#SBATCH --account=YOUR_ACCOUNT   # set to your SLURM project
#SBATCH --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --output=cluster/logs/%A_%a.out

set -euo pipefail

MANIFEST="${1:-cluster/gvns_manifest.csv}"
OUTDIR="${2:-Results/GVNS}"

module load Python/Anaconda 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate olnet

cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"

echo "host=$(hostname) task=${SLURM_ARRAY_TASK_ID} manifest=${MANIFEST}"
python cluster/run_gvns.py --manifest "$MANIFEST" --idx "$SLURM_ARRAY_TASK_ID" --out-dir "$OUTDIR"

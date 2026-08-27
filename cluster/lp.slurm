#!/bin/bash
# Compute LP relaxation + rounded-LP reference bounds for all instances.
#   sbatch cluster/lp.slurm
#
#SBATCH --job-name=olnet_lp
#SBATCH --partition=rocky
#SBATCH --account=proj_1902
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --output=cluster/logs/lp_%j.out

set -euo pipefail
module load Python/Anaconda 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate olnet
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
python cluster/lp_bounds.py --sets synthetic real --out Results/lp_bounds.csv

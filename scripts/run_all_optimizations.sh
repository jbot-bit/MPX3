#!/bin/bash

# Run all ORB optimizations in parallel

cd /c/Users/sydne/OneDrive/Desktop/MPX2_fresh

echo "Starting optimizations for all ORBs..."
echo ""

python optimize_single_orb.py 0900 > results_0900.txt 2>&1 &
PID1=$!

python optimize_single_orb.py 1000 > results_1000.txt 2>&1 &
PID2=$!

python optimize_single_orb.py 1100 > results_1100.txt 2>&1 &
PID3=$!

python optimize_single_orb.py 1800 > results_1800.txt 2>&1 &
PID4=$!

echo "Running optimizations in parallel..."
echo "  0900 ORB: PID $PID1"
echo "  1000 ORB: PID $PID2"
echo "  1100 ORB: PID $PID3"
echo "  1800 ORB: PID $PID4"
echo ""
echo "Waiting for completion..."

wait $PID1
wait $PID2
wait $PID3
wait $PID4

echo ""
echo "All optimizations complete!"
echo ""
echo "Results saved to:"
echo "  results_0900.txt"
echo "  results_1000.txt"
echo "  results_1100.txt"
echo "  results_1800.txt"

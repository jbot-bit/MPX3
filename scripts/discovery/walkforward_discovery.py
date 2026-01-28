"""
Walk-Forward Discovery Pipeline

Complete 9-stage validation to prevent curve-fitting and ensure edge robustness.

Stages:
1. Concept Testing (validation data)
2. Parameter Optimization (training data)
3. Out-of-Sample Verification (test data)
4. Cost Stress Testing
5. Monte Carlo Simulation
6. Regime Analysis
7. Rolling Window Walk-Forward
8. Sample Size & Statistical Validation
9. Final Documentation & Promotion

ONLY edges that pass ALL 9 stages are promoted to production.
"""

import sys
sys.path.append('.')

import duckdb
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from scripts.discovery.concept_tester import test_concept
from scripts.discovery.parameter_optimizer import optimize_parameters
from scripts.discovery.out_of_sample_verifier import verify_out_of_sample

# TODO: Import remaining stages when implemented
# from scripts.discovery.stress_tester import run_stress_tests
# from scripts.discovery.monte_carlo import run_monte_carlo
# from scripts.discovery.regime_analyzer import analyze_regimes
# from scripts.discovery.rolling_window import run_rolling_walkforward
# from scripts.discovery.statistical_validator import validate_statistics


def run_full_pipeline(
    orb_time: str,
    instrument: str = 'MGC',
    use_family_filter: bool = True,
    output_dir: str = 'validation_reports'
) -> Dict:
    """
    Run complete 9-stage validation pipeline

    Args:
        orb_time: '0900', '1000', '1100', '1800', etc.
        instrument: 'MGC', 'NQ', 'MPL'
        use_family_filter: Apply strategy family filtering
        output_dir: Directory to save validation reports

    Returns:
        Complete validation report with all stage results

    Process:
        Stage 1: Concept test on validation data (held-out)
          ↓ PASS
        Stage 2: Optimize parameters on training data
          ↓ PASS
        Stage 3: Verify on test data (unseen)
          ↓ PASS
        Stage 4: Stress test costs
          ↓ PASS
        Stage 5: Monte Carlo simulation
          ↓ PASS
        Stage 6: Regime analysis
          ↓ PASS
        Stage 7: Rolling window walk-forward
          ↓ PASS
        Stage 8: Statistical validation
          ↓ PASS
        Stage 9: Final documentation & promotion
    """
    print("\n" + "="*80)
    print("WALK-FORWARD VALIDATION PIPELINE")
    print("="*80)
    print(f"ORB: {orb_time} | Instrument: {instrument}")
    print(f"Strategy Family Filter: {'ENABLED' if use_family_filter else 'DISABLED'}")
    print("="*80 + "\n")

    con = duckdb.connect('gold.db')

    validation_report = {
        'pipeline': 'walkforward_validation',
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'orb_time': orb_time,
        'instrument': instrument,
        'use_family_filter': use_family_filter,
        'stages': {},
        'overall_verdict': None,
        'all_stages_passed': False
    }

    try:
        # ====================================================================
        # STAGE 1: CONCEPT TESTING
        # ====================================================================
        print("\n" + "█"*80)
        print("STAGE 1/9: CONCEPT TESTING (Validation Data - Held Out)")
        print("█"*80)

        stage1_result = test_concept(
            con=con,
            orb_time=orb_time,
            instrument=instrument,
            use_family_filter=use_family_filter
        )

        validation_report['stages']['stage_1_concept'] = stage1_result.__dict__

        if not stage1_result.valid:
            print("\n❌ PIPELINE STOPPED: Concept failed validation data test")
            print("Do NOT waste time optimizing - the basic idea doesn't work.")
            validation_report['overall_verdict'] = 'REJECTED_STAGE_1'
            validation_report['rejection_reason'] = stage1_result.reason
            return validation_report

        print("\n✅ STAGE 1 PASSED - Concept validated, proceeding to optimization...")

        # ====================================================================
        # STAGE 2: PARAMETER OPTIMIZATION
        # ====================================================================
        print("\n" + "█"*80)
        print("STAGE 2/9: PARAMETER OPTIMIZATION (Training Data Only)")
        print("█"*80)

        stage2_result = optimize_parameters(
            con=con,
            orb_time=orb_time,
            instrument=instrument,
            use_family_filter=use_family_filter
        )

        validation_report['stages']['stage_2_optimization'] = stage2_result.__dict__

        if not stage2_result.passed:
            print("\n❌ PIPELINE STOPPED: No profitable configuration found")
            validation_report['overall_verdict'] = 'REJECTED_STAGE_2'
            validation_report['rejection_reason'] = stage2_result.reason
            return validation_report

        print("\n✅ STAGE 2 PASSED - Optimal parameters found, proceeding to out-of-sample test...")

        # ====================================================================
        # STAGE 3: OUT-OF-SAMPLE VERIFICATION
        # ====================================================================
        print("\n" + "█"*80)
        print("STAGE 3/9: OUT-OF-SAMPLE VERIFICATION (Test Data - UNSEEN)")
        print("█"*80)
        print("CRITICAL: This is the key anti-curve-fitting gate")

        stage3_result = verify_out_of_sample(
            con=con,
            orb_time=orb_time,
            optimal_rr=stage2_result.optimal_rr,
            optimal_filter=stage2_result.optimal_filter,
            optimal_sl_mode=stage2_result.optimal_sl_mode,
            train_expr=stage2_result.train_expr,
            instrument=instrument,
            use_family_filter=use_family_filter
        )

        validation_report['stages']['stage_3_out_of_sample'] = stage3_result.__dict__

        if not stage3_result.passed:
            print("\n❌ PIPELINE STOPPED: Edge fails on unseen data")
            print("This edge was CURVE-FIT to training data and does NOT generalize.")
            validation_report['overall_verdict'] = 'REJECTED_STAGE_3_CURVE_FIT'
            validation_report['rejection_reason'] = stage3_result.reason
            return validation_report

        print("\n✅ STAGE 3 PASSED - Edge survives out-of-sample test")
        print("This is STRONG evidence the edge is NOT curve-fit.")

        # ====================================================================
        # STAGE 4-9: TODO - Implement remaining stages
        # ====================================================================
        print("\n" + "="*80)
        print("STAGES 4-9: TO BE IMPLEMENTED")
        print("="*80)
        print("\nRemaining stages:")
        print("  Stage 4: Cost Stress Testing (+25%, +50%, +100%)")
        print("  Stage 5: Monte Carlo Simulation (luck vs skill)")
        print("  Stage 6: Regime Analysis (high/low vol, trend/range)")
        print("  Stage 7: Rolling Window Walk-Forward (multiple periods)")
        print("  Stage 8: Statistical Validation (sample size, CI, p-value)")
        print("  Stage 9: Final Documentation & Promotion")
        print("\nThese will be implemented in future iterations.")

        # ====================================================================
        # PROVISIONAL PASS (Stages 1-3 only)
        # ====================================================================
        print("\n" + "="*80)
        print("PROVISIONAL VALIDATION STATUS")
        print("="*80)
        print("\n✅ Stages 1-3 PASSED:")
        print(f"  Stage 1: Concept validated (ExpR: {stage1_result.validation_expr:+.3f}R)")
        print(f"  Stage 2: Parameters optimized (Train ExpR: {stage2_result.train_expr:+.3f}R)")
        print(f"  Stage 3: Out-of-sample verified (Test ExpR: {stage3_result.test_expr:+.3f}R, Degradation: {stage3_result.degradation:.1%})")
        print("\n⚠️  Stages 4-9: NOT YET IMPLEMENTED")
        print("\n📊 PROVISIONAL STATUS: PROMISING (but incomplete validation)")
        print("\nOptimal parameters:")
        print(f"  RR:     {stage2_result.optimal_rr}")
        print(f"  Filter: {stage2_result.optimal_filter}")
        print(f"  SL Mode: {stage2_result.optimal_sl_mode}")
        print("\nPerformance summary:")
        print(f"  Validation ExpR: {stage1_result.validation_expr:+.3f}R ({stage1_result.validation_sample} trades)")
        print(f"  Training ExpR:   {stage2_result.train_expr:+.3f}R ({stage2_result.train_sample} trades)")
        print(f"  Test ExpR:       {stage3_result.test_expr:+.3f}R ({stage3_result.test_sample} trades)")
        print(f"  Degradation:     {stage3_result.degradation:.1%}")
        print("="*80 + "\n")

        validation_report['overall_verdict'] = 'PROVISIONAL_PASS_STAGES_1_3'
        validation_report['all_stages_passed'] = False
        validation_report['stages_completed'] = 3
        validation_report['stages_total'] = 9
        validation_report['optimal_parameters'] = {
            'rr': stage2_result.optimal_rr,
            'orb_filter': stage2_result.optimal_filter,
            'sl_mode': stage2_result.optimal_sl_mode
        }
        validation_report['performance_summary'] = {
            'validation_expr': stage1_result.validation_expr,
            'training_expr': stage2_result.train_expr,
            'test_expr': stage3_result.test_expr,
            'degradation': stage3_result.degradation
        }

    except Exception as e:
        print(f"\n❌ PIPELINE ERROR: {e}")
        import traceback
        traceback.print_exc()
        validation_report['overall_verdict'] = 'ERROR'
        validation_report['error'] = str(e)

    finally:
        con.close()

    # Save validation report
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    report_filename = f"walkforward_{instrument}_{orb_time}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = output_path / report_filename

    with open(report_path, 'w') as f:
        json.dump(validation_report, f, indent=2, default=str)

    print(f"\n📄 Validation report saved: {report_path}")

    return validation_report


if __name__ == '__main__':
    """CLI for walk-forward discovery"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run complete 9-stage walk-forward validation pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test 1000 ORB concept on MGC
  python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument MGC

  # Test 1800 ORB on MGC without family filter
  python scripts/discovery/walkforward_discovery.py --orb 1800 --instrument MGC --no-family-filter

  # Test 0900 ORB on NQ
  python scripts/discovery/walkforward_discovery.py --orb 0900 --instrument NQ
        """
    )

    parser.add_argument('--orb', required=True,
                        choices=['0900', '1000', '1100', '1800', '2300', '0030'],
                        help='ORB time to validate')
    parser.add_argument('--instrument', default='MGC',
                        choices=['MGC', 'NQ', 'MPL'],
                        help='Instrument to validate')
    parser.add_argument('--no-family-filter', action='store_true',
                        help='Disable strategy family filtering')
    parser.add_argument('--output-dir', default='validation_reports',
                        help='Directory to save validation reports')

    args = parser.parse_args()

    report = run_full_pipeline(
        orb_time=args.orb,
        instrument=args.instrument,
        use_family_filter=not args.no_family_filter,
        output_dir=args.output_dir
    )

    # Exit with appropriate code
    if report['overall_verdict'] in ['PROVISIONAL_PASS_STAGES_1_3', 'PROMOTED']:
        sys.exit(0)
    else:
        sys.exit(1)

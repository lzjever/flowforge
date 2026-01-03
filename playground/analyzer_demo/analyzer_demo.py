#!/usr/bin/env python
"""
Routine and Workflow Analyzer Demo

This demo automatically analyzes routines and workflows, generating:
- Routine analysis JSON and Markdown cards
- Workflow analysis JSON
- Standard and Ultimate D2 diagrams for both workflows

Usage:
    python -m playground.analyzer_demo.analyzer_demo
"""

import sys
from pathlib import Path

from routilux import (
    Flow, 
    RoutineAnalyzer, 
    WorkflowAnalyzer, 
    analyze_routine_file, 
    analyze_workflow,
    RoutineMarkdownFormatter
)

# Import demo routines - handle both module and script execution
try:
    from .demo_routines import (
        DataCollector,
        DataProcessor,
        DataValidator,
        DataAggregator,
        DataRouter,
        DataSink,
        TaskDispatcher,
        WorkerProcessor,
        ResultAggregator,
        LoopController
    )
except ImportError:
    # If running as script, import from same directory
    from demo_routines import (
        DataCollector,
        DataProcessor,
        DataValidator,
        DataAggregator,
        DataRouter,
        DataSink,
        TaskDispatcher,
        WorkerProcessor,
        ResultAggregator,
        LoopController
    )


def create_complex_workflow() -> Flow:
    """Create a complex demo workflow with loops, task distribution, and aggregation."""
    flow = Flow(
        flow_id="complex_demo_workflow",
        execution_strategy="concurrent",
        max_workers=5,
        execution_timeout=120.0
    )
    
    # Create routine instances
    collector = DataCollector()
    processor = DataProcessor()
    dispatcher = TaskDispatcher()
    
    # Multiple worker processors
    worker1 = WorkerProcessor(worker_id=1)
    worker2 = WorkerProcessor(worker_id=2)
    worker3 = WorkerProcessor(worker_id=3)
    
    result_aggregator = ResultAggregator()
    validator = DataValidator()
    loop_controller = LoopController()
    router = DataRouter()
    
    # Multiple sinks
    sink_high = DataSink()
    sink_medium = DataSink()
    sink_low = DataSink()
    
    # Add routines to flow
    collector_id = flow.add_routine(collector, "collector")
    processor_id = flow.add_routine(processor, "processor")
    dispatcher_id = flow.add_routine(dispatcher, "dispatcher")
    
    worker1_id = flow.add_routine(worker1, "worker1")
    worker2_id = flow.add_routine(worker2, "worker2")
    worker3_id = flow.add_routine(worker3, "worker3")
    
    result_agg_id = flow.add_routine(result_aggregator, "result_aggregator")
    validator_id = flow.add_routine(validator, "validator")
    loop_controller_id = flow.add_routine(loop_controller, "loop_controller")
    router_id = flow.add_routine(router, "router")
    
    sink_high_id = flow.add_routine(sink_high, "sink_high")
    sink_medium_id = flow.add_routine(sink_medium, "sink_medium")
    sink_low_id = flow.add_routine(sink_low, "sink_low")
    
    # Main flow: collector -> processor -> dispatcher
    flow.connect(collector_id, "data", processor_id, "input")
    flow.connect(processor_id, "output", dispatcher_id, "input")
    
    # Task distribution: dispatcher -> workers (parallel)
    flow.connect(dispatcher_id, "worker1", worker1_id, "input")
    flow.connect(dispatcher_id, "worker2", worker2_id, "input")
    flow.connect(dispatcher_id, "worker3", worker3_id, "input")
    
    # Result aggregation: workers -> aggregator
    flow.connect(worker1_id, "result", result_agg_id, "worker1_input")
    flow.connect(worker2_id, "result", result_agg_id, "worker2_input")
    flow.connect(worker3_id, "result", result_agg_id, "worker3_input")
    
    # Aggregation -> validation
    flow.connect(result_agg_id, "aggregated", validator_id, "data")
    
    # Validation -> loop controller
    flow.connect(validator_id, "valid", loop_controller_id, "validation_input")
    flow.connect(validator_id, "invalid", loop_controller_id, "validation_input")
    
    # Loop control: continue loop -> back to processor (creates a cycle)
    flow.connect(loop_controller_id, "continue_loop", processor_id, "input",
                 param_mapping={"data": "processed_data"})
    
    # Loop control: exit loop -> router
    flow.connect(loop_controller_id, "exit_loop", router_id, "input",
                 param_mapping={"final_data": "aggregated_value"})
    
    # Router -> sinks (multiple outputs)
    flow.connect(router_id, "high_priority", sink_high_id, "high_input")
    flow.connect(router_id, "medium_priority", sink_medium_id, "medium_input")
    flow.connect(router_id, "low_priority", sink_low_id, "low_input")
    
    return flow


def create_simple_workflow() -> Flow:
    """Create a simple linear workflow."""
    flow = Flow(flow_id="simple_demo_workflow")
    
    collector = DataCollector()
    processor = DataProcessor()
    sink = DataSink()
    
    collector_id = flow.add_routine(collector, "collector")
    processor_id = flow.add_routine(processor, "processor")
    sink_id = flow.add_routine(sink, "sink")
    
    flow.connect(collector_id, "data", processor_id, "input")
    flow.connect(processor_id, "output", sink_id, "low_input")
    
    return flow


def main():
    """Main function - automatically generates all analyses."""
    print("=" * 80)
    print("ROUTINE AND WORKFLOW ANALYZER DEMO")
    print("=" * 80)
    print()
    
    # Setup paths
    demo_dir = Path(__file__).parent
    export_dir = Path("exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    routine_file = demo_dir / "demo_routines.py"
    
    try:
        # Step 1: Analyze routines
        print("Step 1: Analyzing routines...")
        print("-" * 80)
        print(f"Analyzing: {routine_file.name}")
        
        routine_analysis = analyze_routine_file(routine_file)
        routine_analyzer = RoutineAnalyzer()
        
        # Save routine analysis JSON
        routine_json_file = export_dir / "demo_routines_analysis.json"
        routine_analyzer.save_json(routine_analysis, routine_json_file)
        print(f"✓ Routine analysis JSON saved to: {routine_json_file}")
        
        # Generate Markdown routine cards
        markdown_formatter = RoutineMarkdownFormatter()
        routine_md_file = export_dir / "demo_routines_cards.md"
        markdown_formatter.save(routine_analysis, routine_md_file)
        print(f"✓ Routine Markdown cards saved to: {routine_md_file}")
        print()
        
        # Step 2: Analyze workflows
        print("Step 2: Analyzing workflows...")
        print("-" * 80)
        
        workflow_analyzer = WorkflowAnalyzer()
        
        # Analyze complex workflow
        print("\nAnalyzing complex workflow...")
        complex_flow = create_complex_workflow()
        complex_result = analyze_workflow(complex_flow, include_source_analysis=True)
        
        complex_json_file = export_dir / "complex_demo_workflow_analysis.json"
        workflow_analyzer.save_json(complex_result, complex_json_file)
        print(f"✓ Complex workflow JSON saved to: {complex_json_file}")
        
        # Generate standard D2
        complex_d2_standard = export_dir / "complex_demo_workflow.d2"
        workflow_analyzer.save_d2(complex_result, complex_d2_standard, mode="standard")
        print(f"✓ Complex workflow standard D2 saved to: {complex_d2_standard}")
        
        # Generate ultimate D2 with routine analysis
        complex_d2_ultimate = export_dir / "complex_demo_workflow_ultimate.d2"
        workflow_analyzer.save_d2(complex_result, complex_d2_ultimate, mode="ultimate",
                                 routine_analysis=routine_analysis)
        print(f"✓ Complex workflow ultimate D2 saved to: {complex_d2_ultimate}")
        
        # Analyze simple workflow
        print("\nAnalyzing simple workflow...")
        simple_flow = create_simple_workflow()
        simple_result = analyze_workflow(simple_flow, include_source_analysis=True)
        
        simple_json_file = export_dir / "simple_demo_workflow_analysis.json"
        workflow_analyzer.save_json(simple_result, simple_json_file)
        print(f"✓ Simple workflow JSON saved to: {simple_json_file}")
        
        # Generate standard D2
        simple_d2_standard = export_dir / "simple_demo_workflow.d2"
        workflow_analyzer.save_d2(simple_result, simple_d2_standard, mode="standard")
        print(f"✓ Simple workflow standard D2 saved to: {simple_d2_standard}")
        
        # Generate ultimate D2 with routine analysis
        simple_d2_ultimate = export_dir / "simple_demo_workflow_ultimate.d2"
        workflow_analyzer.save_d2(simple_result, simple_d2_ultimate, mode="ultimate",
                                routine_analysis=routine_analysis)
        print(f"✓ Simple workflow ultimate D2 saved to: {simple_d2_ultimate}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\nExport directory: {export_dir.absolute()}")
        print(f"\nGenerated files:")
        print(f"  📄 Routine Analysis:")
        print(f"     - {routine_json_file.name}")
        print(f"     - {routine_md_file.name}")
        print(f"  📊 Complex Workflow:")
        print(f"     - {complex_json_file.name}")
        print(f"     - {complex_d2_standard.name}")
        print(f"     - {complex_d2_ultimate.name}")
        print(f"  📊 Simple Workflow:")
        print(f"     - {simple_json_file.name}")
        print(f"     - {simple_d2_standard.name}")
        print(f"     - {simple_d2_ultimate.name}")
        
        print("\nNext steps:")
        print("  1. View Markdown cards: cat exports/demo_routines_cards.md")
        print("  2. Generate D2 diagrams:")
        print("     d2 exports/complex_demo_workflow.d2 exports/complex_demo_workflow.svg")
        print("     d2 exports/complex_demo_workflow_ultimate.d2 exports/complex_demo_workflow_ultimate.svg")
        print("     d2 exports/simple_demo_workflow.d2 exports/simple_demo_workflow.svg")
        print("     d2 exports/simple_demo_workflow_ultimate.d2 exports/simple_demo_workflow_ultimate.svg")
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

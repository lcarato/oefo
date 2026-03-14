"""
Command-line interface for OEFO.

Provides commands for:
- Running data scrapers
- Extracting data from PDFs
- Running quality control checks
- Exporting data in various formats
- Viewing database status
- Starting the live dashboard
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional
import json
import logging

from . import __version__

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='oefo',
        description='Open Energy Finance Observatory - Energy finance data toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current configuration
  python -m oefo config

  # Run scraper for all sources
  python -m oefo scrape all

  # Run scraper for a specific source
  python -m oefo scrape ifc --output-dir ./data/raw

  # Extract data from a single PDF
  python -m oefo extract report.pdf --source-type regulatory

  # Batch extract from directory
  python -m oefo extract-batch ./data/raw --source-type dfi

  # Run quality control
  python -m oefo qc --full

  # Export data to Excel
  python -m oefo export --format excel --output results.xlsx

  # Start live dashboard
  python -m oefo dashboard --port 8765

  # View database statistics
  python -m oefo status
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # --- Run (Pipeline Agent) command ---
    run_parser = subparsers.add_parser(
        'run',
        help='Run the full pipeline via the Pipeline Agent'
    )
    run_parser.add_argument(
        '--type',
        choices=['full', 'weekly_dfi', 'monthly_regulatory', 'quarterly_sec', 'qc_only', 'export_only'],
        default='full',
        help='Run type (default: full)'
    )
    run_parser.add_argument(
        '--sources',
        type=str,
        default=None,
        help='Comma-separated list of sources (e.g., ifc,ebrd,gcf)'
    )
    run_parser.add_argument(
        '--skip-scrape',
        action='store_true',
        help='Skip the scraping phase'
    )
    run_parser.add_argument(
        '--skip-extract',
        action='store_true',
        help='Skip the extraction phase'
    )
    run_parser.add_argument(
        '--skip-qc',
        action='store_true',
        help='Skip the QC phase'
    )
    run_parser.add_argument(
        '--skip-export',
        action='store_true',
        help='Skip the export phase'
    )
    run_parser.add_argument(
        '--qc-rules-only',
        action='store_true',
        help='Only run rule-based QC (skip LLM layer)'
    )
    run_parser.add_argument(
        '--force-scrape',
        action='store_true',
        help='Force re-scraping even if data exists'
    )
    run_parser.add_argument(
        '--formats',
        type=str,
        default='excel,csv,parquet',
        help='Comma-separated export formats (default: excel,csv,parquet)'
    )
    run_parser.add_argument(
        '--parallel',
        type=int,
        default=4,
        help='Number of parallel extraction workers (default: 4)'
    )
    run_parser.set_defaults(func=handle_run)

    # --- Scrape command ---
    scrape_parser = subparsers.add_parser(
        'scrape',
        help='Run scraper for specified source(s)'
    )
    scrape_parser.add_argument(
        'source',
        choices=['ifc', 'ebrd', 'gcf', 'sec', 'aneel', 'aer', 'ofgem', 'ferc', 'all'],
        help='Data source to scrape'
    )
    scrape_parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory to save scraped data (default: config RAW_DIR)'
    )
    scrape_parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-scraping even if data exists'
    )
    scrape_parser.set_defaults(func=handle_scrape)

    # --- Extract command ---
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract data from a single PDF'
    )
    extract_parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to PDF file to extract from'
    )
    extract_parser.add_argument(
        '--source-type',
        required=True,
        choices=['regulatory', 'dfi', 'corporate', 'bond'],
        help='Type of document (determines extraction prompt)'
    )
    extract_parser.add_argument(
        '--output',
        type=str,
        help='Output path for extracted data (JSON)'
    )
    extract_parser.add_argument(
        '--language',
        type=str,
        default=None,
        help='Document language (en, pt, es, de, fr)'
    )
    extract_parser.set_defaults(func=handle_extract)

    # --- Extract batch command ---
    extract_batch_parser = subparsers.add_parser(
        'extract-batch',
        help='Extract data from all PDFs in a directory'
    )
    extract_batch_parser.add_argument(
        'directory',
        type=str,
        help='Directory containing PDF files'
    )
    extract_batch_parser.add_argument(
        '--source-type',
        required=True,
        choices=['regulatory', 'dfi', 'corporate', 'bond'],
        help='Type of documents'
    )
    extract_batch_parser.add_argument(
        '--output-dir',
        type=str,
        help='Directory to save extracted data'
    )
    extract_batch_parser.add_argument(
        '--pattern',
        type=str,
        default='*.pdf',
        help='File pattern to match (default: *.pdf)'
    )
    extract_batch_parser.add_argument(
        '--language',
        type=str,
        default=None,
        help='Document language (en, pt, es, de, fr)'
    )
    extract_batch_parser.add_argument(
        '--parallel',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    extract_batch_parser.set_defaults(func=handle_extract_batch)

    # --- QC command ---
    qc_parser = subparsers.add_parser(
        'qc',
        help='Run quality control checks on extracted data'
    )
    qc_parser.add_argument(
        '--rules-only',
        action='store_true',
        help='Only run rule-based checks (Layer 1)'
    )
    qc_parser.add_argument(
        '--full',
        action='store_true',
        help='Run all 3 layers including LLM review'
    )
    qc_parser.add_argument(
        '--input',
        type=str,
        help='Path to extracted data directory or JSON file'
    )
    qc_parser.add_argument(
        '--output',
        type=str,
        help='Path to save QC report'
    )
    qc_parser.set_defaults(func=handle_qc)

    # --- Export command ---
    export_parser = subparsers.add_parser(
        'export',
        help='Export database in specified format'
    )
    export_parser.add_argument(
        '--format',
        required=True,
        choices=['excel', 'csv', 'parquet', 'json'],
        help='Output format'
    )
    export_parser.add_argument(
        '--output',
        required=True,
        type=str,
        help='Output file path'
    )
    export_parser.add_argument(
        '--input',
        type=str,
        help='Input data path (default: uses configured FINAL_DIR)'
    )
    export_parser.add_argument(
        '--filter',
        type=str,
        help='Filter expression (e.g., "country==\'Brazil\'")'
    )
    export_parser.set_defaults(func=handle_export)

    # --- Dashboard command ---
    dashboard_parser = subparsers.add_parser(
        'dashboard',
        help='Start the live SSE dashboard'
    )
    dashboard_parser.add_argument(
        '--port',
        type=int,
        default=8765,
        help='Port for SSE server (default: 8765)'
    )
    dashboard_parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind (default: 127.0.0.1)'
    )
    dashboard_parser.add_argument(
        '--public',
        action='store_true',
        help='Enable public access with wildcard CORS (overrides host to 0.0.0.0)'
    )
    dashboard_parser.set_defaults(func=handle_dashboard)

    # --- Status command ---
    status_parser = subparsers.add_parser(
        'status',
        help='Show database statistics and pipeline status'
    )
    status_parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed statistics'
    )
    status_parser.set_defaults(func=handle_status)

    # --- Config command ---
    config_parser = subparsers.add_parser(
        'config',
        help='Show current configuration'
    )
    config_parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate API keys and directories'
    )
    config_parser.set_defaults(func=handle_config)

    return parser


# ─── Command Handlers ────────────────────────────────────────────────────────

def handle_scrape(args: argparse.Namespace) -> int:
    """Handle scrape command."""
    try:
        from .scrapers import get_scraper, list_scrapers
        from .config.settings import RAW_DIR

        output_dir = Path(args.output_dir) if args.output_dir else RAW_DIR

        if args.source == 'all':
            sources = list_scrapers()
        else:
            sources = [args.source.upper()]

        print(f"OEFO Scraper — collecting documents from {len(sources)} source(s)")
        print(f"Output directory: {output_dir}")
        print()

        total_docs = 0
        for source_name in sources:
            try:
                print(f"  [{source_name}] Scraping...", end=" ", flush=True)
                scraper = get_scraper(source_name)
                documents = scraper.scrape(
                    output_dir=str(output_dir / source_name.lower()),
                    force=args.force
                )
                count = len(documents) if documents else 0
                total_docs += count
                print(f"✓ {count} documents downloaded")
            except Exception as e:
                print(f"✗ Error: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()

        print(f"\nScraping complete: {total_docs} documents collected")
        return 0

    except Exception as e:
        print(f"Error during scraping: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_extract(args: argparse.Namespace) -> int:
    """Handle extract command for a single PDF."""
    try:
        from .extraction import ExtractionPipeline

        pdf_path = Path(args.pdf_path)
        if not pdf_path.exists():
            print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
            return 1

        pipeline = ExtractionPipeline()

        print(f"OEFO Extraction Pipeline")
        print(f"  Document: {pdf_path.name}")
        print(f"  Source type: {args.source_type}")
        if args.language:
            print(f"  Language: {args.language}")
        print()

        results = pipeline.extract(
            pdf_path=str(pdf_path),
            source_type=args.source_type,
            language=args.language,
            source_document_url=str(pdf_path.resolve()),
            source_document_id=pdf_path.stem,
        )

        # Show results summary
        print(f"Extraction complete: {len(results)} page results")
        for r in results:
            tier = r.tier if hasattr(r, 'tier') else 'unknown'
            conf = r.confidence if hasattr(r, 'confidence') else 0
            traceable = '✓' if hasattr(r, 'has_full_traceability') and r.has_full_traceability else '○'
            print(f"  Page {r.page_num}: Tier {tier}, confidence {conf:.0%}, traceability {traceable}")

        # Save output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump([r.to_dict() for r in results], f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_extract_batch(args: argparse.Namespace) -> int:
    """Handle extract-batch command."""
    try:
        from .extraction import ExtractionPipeline
        from .config.settings import EXTRACTED_DIR

        directory = Path(args.directory)
        if not directory.is_dir():
            print(f"Error: Directory not found: {directory}", file=sys.stderr)
            return 1

        pdf_files = sorted(directory.glob(args.pattern))
        if not pdf_files:
            print(f"No PDF files found matching '{args.pattern}' in {directory}", file=sys.stderr)
            return 1

        output_dir = Path(args.output_dir) if args.output_dir else EXTRACTED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        pipeline = ExtractionPipeline()

        print(f"OEFO Batch Extraction")
        print(f"  Documents: {len(pdf_files)} PDFs")
        print(f"  Source type: {args.source_type}")
        print(f"  Output: {output_dir}")
        print()

        success = 0
        errors = 0
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                print(f"  [{i}/{len(pdf_files)}] {pdf_file.name}...", end=" ", flush=True)
                results = pipeline.extract(
                    pdf_path=str(pdf_file),
                    source_type=args.source_type,
                    language=args.language,
                    source_document_url=str(pdf_file.resolve()),
                    source_document_id=pdf_file.stem,
                )
                # Save per-document JSON
                out_file = output_dir / f"{pdf_file.stem}.json"
                with open(out_file, 'w') as f:
                    json.dump([r.to_dict() for r in results], f, indent=2, default=str)
                print(f"✓ {len(results)} pages")
                success += 1
            except Exception as e:
                print(f"✗ {e}")
                errors += 1
                if args.verbose:
                    import traceback
                    traceback.print_exc()

        print(f"\nBatch complete: {success} succeeded, {errors} failed")
        return 0 if errors == 0 else 1

    except Exception as e:
        print(f"Error during batch extraction: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_qc(args: argparse.Namespace) -> int:
    """Handle qc command."""
    try:
        from .qc import QCAgent
        from .config.settings import EXTRACTED_DIR, FINAL_DIR

        enable_llm = args.full and not args.rules_only

        agent = QCAgent(
            enable_rules=True,
            enable_stats=not args.rules_only,
            enable_llm=enable_llm,
        )

        mode = "rules-only" if args.rules_only else ("full (3-layer)" if args.full else "standard (rules + stats)")
        print(f"OEFO Quality Control — mode: {mode}")

        input_path = Path(args.input) if args.input else EXTRACTED_DIR

        # Load extracted JSON files
        if input_path.is_dir():
            json_files = list(input_path.glob("*.json"))
            print(f"  Loading {len(json_files)} extraction files from {input_path}")
        elif input_path.is_file():
            json_files = [input_path]
        else:
            print(f"Error: Input not found: {input_path}", file=sys.stderr)
            return 1

        # Process observations
        from .models import Observation
        observations = []
        for jf in json_files:
            try:
                with open(jf) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'extracted_data' in item:
                            # Convert extraction results to observations
                            obs_data = item.get('extracted_data', {})
                            if obs_data:
                                observations.append(obs_data)
            except Exception as e:
                logger.warning(f"Could not load {jf}: {e}")

        print(f"  Found {len(observations)} observations to validate")
        print()

        if not observations:
            print("No observations found to validate. Run extraction first.")
            return 0

        # Run QC (batch)
        results = agent.process_batch(
            observations=observations,
            existing_observations=[],
        )

        # Print summary
        auto = len(results.get('auto_accepted', []))
        flagged = len(results.get('flagged_for_review', []))
        rejected = len(results.get('rejected', []))

        print(f"\nQC Results:")
        print(f"  ✓ Auto-accepted (score ≥ 0.85): {auto}")
        print(f"  ⚠ Flagged for review (0.50–0.85): {flagged}")
        print(f"  ✗ Rejected (score < 0.50): {rejected}")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n  QC report saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"Error during QC: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_export(args: argparse.Namespace) -> int:
    """Handle export command."""
    try:
        import pandas as pd
        from .config.settings import FINAL_DIR

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load data
        input_path = Path(args.input) if args.input else FINAL_DIR
        print(f"OEFO Export — format: {args.format.upper()}")
        print(f"  Input: {input_path}")
        print(f"  Output: {output_path}")

        # Try to load observations from JSON files
        records = []
        if input_path.is_dir():
            for jf in input_path.glob("*.json"):
                try:
                    with open(jf) as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    elif isinstance(data, dict):
                        records.append(data)
                except Exception:
                    pass

        if not records:
            print("  Warning: No data found. Generating sample output.")
            df = pd.DataFrame({
                'country': ['Brazil', 'India', 'Germany', 'USA', 'UK'],
                'technology': ['Solar PV', 'Onshore Wind', 'Offshore Wind', 'Hydro', 'Biomass'],
                'wacc_percent': [8.5, 7.2, 5.8, 6.1, 9.3],
                'cost_of_debt_percent': [6.2, 5.8, 3.5, 4.2, 7.1],
                'cost_of_equity_percent': [12.5, 10.1, 8.2, 9.5, 13.0],
                'leverage_percent': [65, 70, 60, 55, 50],
                'source': ['IFC', 'EBRD', 'Ofgem', 'FERC', 'ANEEL'],
                'year': [2024, 2024, 2024, 2024, 2024],
            })
        else:
            df = pd.DataFrame(records)

        # Apply filter if specified
        if args.filter:
            df = df.query(args.filter)

        # Export
        if args.format == 'excel':
            from .outputs.excel import ExcelOutputGenerator
            gen = ExcelOutputGenerator()
            gen.generate_workbook(df, str(output_path))
        elif args.format == 'csv':
            from .outputs.csv_export import export_csv
            export_csv(df, str(output_path))
        elif args.format == 'parquet':
            from .outputs.csv_export import export_parquet
            export_parquet(df, str(output_path))
        elif args.format == 'json':
            from .outputs.csv_export import export_json
            export_json(df, str(output_path))

        print(f"\n  Export complete: {output_path}")
        return 0

    except Exception as e:
        print(f"Error during export: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_dashboard(args: argparse.Namespace) -> int:
    """Handle dashboard command — start SSE server."""
    try:
        from .dashboard.server import start_server

        # If --public flag is set, use 0.0.0.0 host and enable CORS wildcard
        host = args.host
        cors_origin = None
        if args.public:
            host = "0.0.0.0"
            cors_origin = "*"

        print(f"OEFO Live Dashboard")
        print(f"  Server: http://{host}:{args.port}")
        if args.public:
            print(f"  Mode: PUBLIC (CORS enabled)")
        else:
            print(f"  Mode: LOCALHOST ONLY")
        print(f"  Press Ctrl+C to stop")
        print()

        start_server(host=host, port=args.port, cors_origin=cors_origin)
        return 0

    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        return 0
    except Exception as e:
        print(f"Error starting dashboard: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_status(args: argparse.Namespace) -> int:
    """Handle status command."""
    try:
        from .config.settings import (
            DATA_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR,
            ANTHROPIC_API_KEY, OPENAI_API_KEY, LLM_PROVIDER
        )

        print("OEFO Pipeline Status")
        print("=" * 60)

        # Check directories
        raw_count = len(list(RAW_DIR.glob("**/*.pdf"))) if RAW_DIR.exists() else 0
        extracted_count = len(list(EXTRACTED_DIR.glob("*.json"))) if EXTRACTED_DIR.exists() else 0
        final_count = len(list(FINAL_DIR.glob("*.json"))) if FINAL_DIR.exists() else 0

        print(f"\nData Pipeline:")
        print(f"  Raw documents (PDFs):     {raw_count}")
        print(f"  Extracted (JSON):         {extracted_count}")
        print(f"  QC-approved (final):      {final_count}")

        print(f"\nConfiguration:")
        print(f"  LLM provider:             {LLM_PROVIDER}")
        print(f"  Cloud API key configured: {'Yes' if (ANTHROPIC_API_KEY or OPENAI_API_KEY) else 'No ⚠'}")
        print(f"  Data directory:           {DATA_DIR}")

        if args.detailed:
            print(f"\nDirectory Sizes:")
            for name, d in [("Raw", RAW_DIR), ("Extracted", EXTRACTED_DIR), ("Final", FINAL_DIR)]:
                if d.exists():
                    size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                    print(f"  {name:.<30} {size / 1024 / 1024:.1f} MB")

            if RAW_DIR.exists():
                print(f"\nRaw Documents by Source:")
                for source_dir in sorted(RAW_DIR.iterdir()):
                    if source_dir.is_dir():
                        pdfs = list(source_dir.glob("*.pdf"))
                        print(f"  {source_dir.name:.<30} {len(pdfs)} PDFs")

        return 0

    except Exception as e:
        print(f"Error getting status: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_config(args: argparse.Namespace) -> int:
    """Handle config command."""
    try:
        from .config.settings import get_config, print_config, validate_api_keys, validate_directories

        if args.validate:
            print("OEFO Configuration Validation")
            print("=" * 60)
            api_ok = validate_api_keys()
            dir_ok = validate_directories()
            print(f"\n  API keys:    {'✓ Valid' if api_ok else '✗ Missing'}")
            print(f"  Directories: {'✓ Valid' if dir_ok else '✗ Issue detected'}")
            return 0 if (api_ok and dir_ok) else 1
        else:
            print_config()
            return 0

    except Exception as e:
        print(f"Error reading config: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_run(args: argparse.Namespace) -> int:
    """Handle run command — execute Pipeline Agent."""
    try:
        from .agent import PipelineAgent, RunType

        run_type = RunType(args.type)
        sources = args.sources.split(",") if args.sources else None
        export_formats = args.formats.split(",") if args.formats else ["excel", "csv", "parquet"]

        agent = PipelineAgent(
            run_type=run_type,
            sources=sources,
            qc_full=not args.qc_rules_only,
            export_formats=export_formats,
            skip_scrape=args.skip_scrape,
            skip_extract=args.skip_extract,
            skip_qc=args.skip_qc,
            skip_export=args.skip_export,
            force_scrape=args.force_scrape,
            parallel_workers=args.parallel,
            verbose=getattr(args, 'verbose', False),
        )

        report = agent.run()

        if report.overall_success:
            return 0
        elif report.halted:
            return 2
        else:
            return 1

    except Exception as e:
        print(f"Error running Pipeline Agent: {e}", file=sys.stderr)
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Configure logging
    if hasattr(args, 'verbose') and args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 0

    # Call the appropriate handler
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())

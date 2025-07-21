#!/usr/bin/env python3
"""
Enhanced CLI for pie_extractor with comprehensive features.
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Import enhanced modules
from .enhanced_extractor import DocumentExtractor, DocumentExtractionConfig
from .rate_manager import RateLimitConfig
from .model_manager import FallbackConfig
from .exceptions import PieExtractorError, format_error_for_user


def create_parser() -> argparse.ArgumentParser:
    """Create the enhanced argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced document extraction using dual AI models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Enhanced Features:
  • Dual-model architecture (vision + reasoning)
  • Automatic API key rotation and rate limiting
  • Intelligent model fallback strategies
  • Optional RAG knowledge augmentation
  • Comprehensive performance monitoring

Examples:
  %(prog)s document.jpg -o output.json
  %(prog)s ./documents -o ./output --batch
  %(prog)s invoice.png --enable-rag --reasoning-model deepseek/deepseek-r1-0528:free
  %(prog)s document.jpg --debug --performance-mode
        """
    )
    
    # Input/Output
    parser.add_argument("input", type=Path, help="Input file or directory")
    parser.add_argument("-o", "--output", type=Path, help="Output file or directory")
    
    # Model Configuration
    parser.add_argument("--vision-model", 
                       default="meta-llama/llama-3.2-11b-vision-instruct:free",
                       help="Vision model for text extraction (default: %(default)s)")
    
    parser.add_argument("--reasoning-model",
                       default="deepseek/deepseek-r1-0528:free", 
                       help="Reasoning model for document analysis (default: %(default)s)")
    
    parser.add_argument("--vision-tokens", type=int, default=4000,
                       help="Max tokens for vision model (default: %(default)s)")
    
    parser.add_argument("--reasoning-tokens", type=int, default=8000,
                       help="Max tokens for reasoning model (default: %(default)s)")
    
    # Processing Options
    parser.add_argument("--batch", action="store_true",
                       help="Process multiple files in directory")
    
    parser.add_argument("--enable-rag", action="store_true",
                       help="Enable RAG knowledge augmentation")
    
    parser.add_argument("--rag-candidates", type=int, default=5,
                       help="Number of RAG candidates to consider (default: %(default)s)")
    
    # Performance & Monitoring
    parser.add_argument("--performance-mode", action="store_true",
                       help="Enable detailed performance monitoring")
    
    parser.add_argument("--rate-limit", type=int, default=20,
                       help="Rate limit (requests per minute) (default: %(default)s)")
    
    parser.add_argument("--key-threshold", type=int, default=40,
                       help="API key switch threshold (default: %(default)s)")
    
    # System Operations
    parser.add_argument("--health-check", action="store_true",
                       help="Perform comprehensive health check")
    
    parser.add_argument("--stats", action="store_true",
                       help="Show system statistics")
    
    parser.add_argument("--discover-models", action="store_true",
                       help="Discover and cache available models")
    
    # Debugging
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    return parser


def perform_health_check(extractor: DocumentExtractor) -> bool:
    """Perform comprehensive health check."""
    print("🏥 Comprehensive Health Check")
    print("=" * 50)
    
    try:
        stats = extractor.get_system_stats()
        
        # Check rate limiting
        rate_stats = stats["rate_limiting"]
        print(f"🔑 API Key Management:")
        print(f"   Current instance: {rate_stats['current_instance']}")
        print(f"   Active keys: {len(rate_stats['keys'])}")
        print(f"   Total requests today: {rate_stats['total_requests_today']}")
        
        # Check model management
        model_stats = stats["model_management"]
        print(f"\n🤖 Model Management:")
        print(f"   Total models: {model_stats['total_models']}")
        print(f"   Free models: {model_stats['free_models']}")
        print(f"   Vision models: {model_stats['vision_models']}")
        print(f"   Failed models: {model_stats['failed_models']}")
        
        # Check RAG system
        print(f"\n🔍 RAG System:")
        print(f"   Enabled: {stats['rag_enabled']}")
        
        # Overall health assessment
        healthy = (
            len(rate_stats['keys']) > 0 and
            model_stats['total_models'] > 0 and
            model_stats['failed_models'] < model_stats['total_models'] * 0.5
        )
        
        print(f"\n{'✅ SYSTEM HEALTHY' if healthy else '❌ SYSTEM ISSUES DETECTED'}")
        return healthy
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def show_system_stats(extractor: DocumentExtractor):
    """Display comprehensive system statistics."""
    print("📊 System Statistics")
    print("=" * 50)
    
    try:
        stats = extractor.get_system_stats()
        
        # Rate limiting stats
        print("🔑 Rate Limiting & API Keys:")
        rate_stats = stats["rate_limiting"]
        for key_info in rate_stats["keys"]:
            status = "🟢" if key_info["is_active"] else "🔴"
            balance = "💰" if key_info["balance_threshold_met"] else "🆓"
            print(f"   {status} {balance} Key {key_info['key_id']}: {key_info['daily_requests']}/{key_info['daily_limit']} requests")
        
        # Model stats
        print(f"\n🤖 Model Management:")
        model_stats = stats["model_management"]
        for category, count in model_stats["models_by_category"].items():
            print(f"   {category}: {count} models")
        
        # Recent timing
        if stats.get("recent_timings"):
            print(f"\n⏱️ Recent Performance:")
            for operation, time_taken in stats["recent_timings"].items():
                print(f"   {operation}: {time_taken:.3f}s")
        
        # Configuration
        print(f"\n⚙️ Configuration:")
        config = stats["config"]
        print(f"   Vision model: {config['vision_model']}")
        print(f"   Reasoning model: {config['reasoning_model']}")
        print(f"   RAG enabled: {config['enable_rag']}")
        print(f"   Max file size: {config['max_file_size_mb']}MB")
        
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")


def process_single_file(extractor: DocumentExtractor, input_path: Path, output_path: Path, verbose: bool = False):
    """Process a single document file."""
    print(f"📄 Processing: {input_path.name}")
    
    try:
        # Process document
        result = extractor.process_document(input_path)
        
        # Save results
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result.__dict__, f, indent=2, default=str)
        
        # Display results
        print(f"✅ Processing complete!")
        print(f"   📊 Quality: {result.accuracy_metrics['overall_quality_score']:.1%}")
        print(f"   ⏱️ Time: {result.processing_time.get('process_document', 0):.2f}s")
        print(f"   📁 Output: {output_path}")
        
        if verbose:
            print(f"   🎯 Text accuracy: {result.accuracy_metrics['text_extraction_accuracy']:.1%}")
            print(f"   📐 Coordinate accuracy: {result.accuracy_metrics['coordinate_accuracy']:.1%}")
            print(f"   🏗️ Structure accuracy: {result.accuracy_metrics['structure_recognition_accuracy']:.1%}")
            
            print(f"   🤖 Models used:")
            for model_type, model_id in result.model_versions.items():
                print(f"      {model_type}: {model_id}")
        
        return result
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        raise


def process_batch(extractor: DocumentExtractor, input_dir: Path, output_dir: Path, verbose: bool = False):
    """Process multiple files in batch."""
    # Find supported files
    supported_exts = {'.png', '.jpg', '.jpeg', '.tiff', '.webp'}
    files = [f for f in input_dir.rglob("*") if f.is_file() and f.suffix.lower() in supported_exts]
    
    if not files:
        print(f"❌ No supported files found in {input_dir}")
        return
    
    print(f"📁 Processing {len(files)} files in batch mode...")
    
    successful = 0
    failed = 0
    total_time = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_path.name}")
        
        try:
            # Determine output path
            relative_path = file_path.relative_to(input_dir)
            output_file = output_dir / relative_path.with_suffix('.json')
            
            # Process file
            result = process_single_file(extractor, file_path, output_file, verbose)
            successful += 1
            total_time += result.processing_time.get('process_document', 0)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1
    
    # Summary
    print(f"\n📊 Batch Processing Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏱️ Total time: {total_time:.2f}s")
    print(f"   📈 Average: {total_time/max(successful, 1):.2f}s per file")
    print(f"   📁 Results in: {output_dir}")


def main():
    """Enhanced main CLI function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create configuration
        config = DocumentExtractionConfig(
            vision_model=args.vision_model,
            reasoning_model=args.reasoning_model,
            vision_max_tokens=args.vision_tokens,
            reasoning_max_tokens=args.reasoning_tokens,
            enable_rag=args.enable_rag,
            rag_search_candidates=args.rag_candidates
        )
        
        rate_config = RateLimitConfig(
            requests_per_minute=args.rate_limit,
            key_switch_threshold=args.key_threshold
        )
        
        fallback_config = FallbackConfig(
            strategy="performance",
            prefer_free_models=True
        )
        
        # Create enhanced extractor
        print("🚀 Initializing Enhanced Document Extractor...")
        extractor = DocumentExtractor(config, rate_config, fallback_config)
        print("✅ Initialization complete!")
        
        # Handle system operations
        if args.health_check:
            healthy = perform_health_check(extractor)
            sys.exit(0 if healthy else 1)
        
        if args.stats:
            show_system_stats(extractor)
            return
        
        if args.discover_models:
            print("🔍 Discovering available models...")
            success = extractor.model_registry.discover_models(force_refresh=True)
            print(f"{'✅' if success else '❌'} Model discovery {'completed' if success else 'failed'}")
            return
        
        # Validate input
        input_path = args.input
        if not input_path.exists():
            print(f"❌ Input path does not exist: {input_path}")
            sys.exit(1)
        
        # Process documents
        if args.batch or input_path.is_dir():
            # Batch processing
            if input_path.is_file():
                print("❌ --batch flag requires a directory input")
                sys.exit(1)
            
            output_dir = args.output or input_path / "extracted"
            process_batch(extractor, input_path, output_dir, args.verbose)
            
        else:
            # Single file processing
            if not input_path.is_file():
                print(f"❌ Input must be a file: {input_path}")
                sys.exit(1)
            
            output_path = args.output or input_path.with_suffix('.json')
            process_single_file(extractor, input_path, output_path, args.verbose)
        
        # Show final stats if performance mode
        if args.performance_mode:
            print(f"\n📊 Final System Statistics:")
            show_system_stats(extractor)
    
    except PieExtractorError as e:
        print(f"❌ {format_error_for_user(e)}")
        if args.debug:
            logging.exception("Detailed error information:")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹ Processing interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.debug:
            logging.exception("Detailed error information:")
        sys.exit(1)


if __name__ == "__main__":
    main()

import json
from typing import List, Dict, Tuple
from pathlib import Path


class ExtractionEvaluator:
    """Evaluates extraction accuracy against ground truth."""
    
    EVALUATED_FIELDS = [
        'product_line',
        'origin_port_code',
        'origin_port_name',
        'destination_port_code',
        'destination_port_name',
        'incoterm',
        'cargo_weight_kg',
        'cargo_cbm',
        'is_dangerous'
    ]
    
    def __init__(self, ground_truth_path: str, output_path: str):
        """
        Initialize evaluator with ground truth and output data.
        
        Args:
            ground_truth_path: Path to ground truth JSON
            output_path: Path to extraction output JSON
        """
        self.ground_truth = self._load_json(ground_truth_path)
        self.output = self._load_json(output_path)
        
        # Create lookup dictionaries by ID
        self.gt_lookup = {item['id']: item for item in self.ground_truth}
        self.out_lookup = {item['id']: item for item in self.output}
        
        # Validate IDs match
        gt_ids = set(self.gt_lookup.keys())
        out_ids = set(self.out_lookup.keys())
        
        if gt_ids != out_ids:
            missing_in_output = gt_ids - out_ids
            extra_in_output = out_ids - gt_ids
            if missing_in_output:
                print(f"⚠ Warning: Missing IDs in output: {missing_in_output}")
            if extra_in_output:
                print(f"⚠ Warning: Extra IDs in output: {extra_in_output}")
    
    def _load_json(self, filepath: str) -> List[Dict]:
        """Load JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _compare_values(self, gt_value, out_value, field_name: str) -> bool:
        """
        Compare two values with field-specific rules.
        
        Args:
            gt_value: Ground truth value
            out_value: Output value
            field_name: Name of field being compared
            
        Returns:
            True if values match, False otherwise
        """
        # Handle null comparisons
        if gt_value is None and out_value is None:
            return True
        if gt_value is None or out_value is None:
            return False
        
        # String comparisons: case-insensitive, whitespace trimmed
        if isinstance(gt_value, str) and isinstance(out_value, str):
            return gt_value.strip().lower() == out_value.strip().lower()
        
        # Float comparisons: exact match after rounding to 2 decimals
        if isinstance(gt_value, (int, float)) and isinstance(out_value, (int, float)):
            return round(float(gt_value), 2) == round(float(out_value), 2)
        
        # Boolean comparisons
        if isinstance(gt_value, bool) and isinstance(out_value, bool):
            return gt_value == out_value
        
        # Fallback: direct comparison
        return gt_value == out_value
    
    def evaluate_field(self, field_name: str) -> Tuple[int, int, List[str]]:
        """
        Evaluate accuracy for a specific field.
        
        Args:
            field_name: Name of field to evaluate
            
        Returns:
            Tuple of (correct_count, total_count, incorrect_ids)
        """
        correct = 0
        total = 0
        incorrect_ids = []
        
        for email_id in self.gt_lookup.keys():
            if email_id not in self.out_lookup:
                total += 1
                incorrect_ids.append(email_id)
                continue
            
            gt_item = self.gt_lookup[email_id]
            out_item = self.out_lookup[email_id]
            
            gt_value = gt_item.get(field_name)
            out_value = out_item.get(field_name)
            
            total += 1
            if self._compare_values(gt_value, out_value, field_name):
                correct += 1
            else:
                incorrect_ids.append(email_id)
        
        return correct, total, incorrect_ids
    
    def evaluate_all(self) -> Dict[str, Dict]:
        """
        Evaluate accuracy across all fields.
        
        Returns:
            Dictionary with per-field and overall metrics
        """
        results = {}
        total_correct = 0
        total_fields = 0
        
        for field in self.EVALUATED_FIELDS:
            correct, total, incorrect_ids = self.evaluate_field(field)
            accuracy = (correct / total * 100) if total > 0 else 0
            
            results[field] = {
                'correct': correct,
                'total': total,
                'accuracy': accuracy,
                'incorrect_ids': incorrect_ids
            }
            
            total_correct += correct
            total_fields += total
        
        # Calculate overall accuracy
        overall_accuracy = (total_correct / total_fields * 100) if total_fields > 0 else 0
        
        results['overall'] = {
            'correct': total_correct,
            'total': total_fields,
            'accuracy': overall_accuracy
        }
        
        return results
    
    def print_report(self, results: Dict[str, Dict]):
        """
        Print formatted evaluation report.
        
        Args:
            results: Results from evaluate_all()
        """
        print("\n" + "="*70)
        print(" "*20 + "EXTRACTION ACCURACY REPORT")
        print("="*70)
        
        print("\nPER-FIELD ACCURACY:")
        print("-"*70)
        print(f"{'Field':<30} {'Correct':<10} {'Total':<10} {'Accuracy':<10}")
        print("-"*70)
        
        for field in self.EVALUATED_FIELDS:
            metrics = results[field]
            print(f"{field:<30} {metrics['correct']:<10} {metrics['total']:<10} {metrics['accuracy']:>6.2f}%")
        
        print("-"*70)
        overall = results['overall']
        print(f"{'OVERALL':<30} {overall['correct']:<10} {overall['total']:<10} {overall['accuracy']:>6.2f}%")
        print("="*70)
        
        # Rating
        accuracy = overall['accuracy']
        if accuracy >= 90:
            rating = "EXCEPTIONAL ⭐⭐⭐"
        elif accuracy >= 80:
            rating = "STRONG ⭐⭐"
        elif accuracy >= 70:
            rating = "ACCEPTABLE ⭐"
        else:
            rating = "NEEDS IMPROVEMENT"
        
        print(f"\nRating: {rating}")
        print()
    
    def print_detailed_errors(self, results: Dict[str, Dict], max_examples: int = 5):
        """
        Print detailed information about errors for debugging.
        
        Args:
            results: Results from evaluate_all()
            max_examples: Maximum number of examples to show per field
        """
        print("\n" + "="*70)
        print(" "*20 + "DETAILED ERROR ANALYSIS")
        print("="*70)
        
        for field in self.EVALUATED_FIELDS:
            metrics = results[field]
            incorrect_ids = metrics['incorrect_ids']
            
            if not incorrect_ids:
                continue
            
            print(f"\n{field.upper()} - {len(incorrect_ids)} errors")
            print("-"*70)
            
            for i, email_id in enumerate(incorrect_ids[:max_examples], 1):
                gt_item = self.gt_lookup.get(email_id, {})
                out_item = self.out_lookup.get(email_id, {})
                
                gt_value = gt_item.get(field, 'MISSING')
                out_value = out_item.get(field, 'MISSING')
                
                print(f"  {i}. {email_id}")
                print(f"     Expected: {gt_value}")
                print(f"     Got:      {out_value}")
            
            if len(incorrect_ids) > max_examples:
                print(f"     ... and {len(incorrect_ids) - max_examples} more")
        
        print()


def main():
    """Main execution function."""
    ground_truth_path = "ground_truth.json"
    output_path = "output.json"
    
    # Check if files exist
    if not Path(ground_truth_path).exists():
        print(f"Error: {ground_truth_path} not found")
        return
    if not Path(output_path).exists():
        print(f"Error: {output_path} not found")
        print("Please run extract.py first to generate output.json")
        return
    
    # Run evaluation
    evaluator = ExtractionEvaluator(ground_truth_path, output_path)
    results = evaluator.evaluate_all()
    
    # Print reports
    evaluator.print_report(results)
    
    # Ask if user wants detailed error analysis
    print("Show detailed error analysis? (y/n): ", end="")
    try:
        show_details = input().strip().lower() == 'y'
        if show_details:
            evaluator.print_detailed_errors(results)
    except:
        pass  # If input not available (non-interactive), skip


if __name__ == "__main__":
    main()
"""
Test ANTLR profiling support
"""
import unittest
from pssparser import Parser

class TestProfiling(unittest.TestCase):
    
    def test_profiling_basic(self):
        """Test basic profiling functionality"""
        parser = Parser()
        parser.enable_profiling(True)
        
        # Parse a simple PSS file
        parser.parses([
            ("test.pss", """
             component pss_top {
                 action A {
                     int x;
                     constraint x > 10;
                 }
                 action B {
                     int y;
                 }
             }
             """),
        ])
        
        # Get profiling info
        profile = parser.get_profile_info()
        
        self.assertIsNotNone(profile, "Profile info should not be None when profiling is enabled")
        
        # Check aggregate stats
        print(f"\n=== Profiling Results ===")
        print(f"Total time in prediction: {profile.total_time_in_prediction} ns")
        print(f"Total SLL lookahead ops: {profile.total_sll_lookahead_ops}")
        print(f"Total LL lookahead ops: {profile.total_ll_lookahead_ops}")
        print(f"DFA size: {profile.dfa_size}")
        
        # Check decision-level info
        decisions = profile.get_decision_info()
        print(f"\nNumber of decisions: {len(decisions)}")
        
        # Show top 5 most expensive decisions
        sorted_decisions = sorted(decisions, key=lambda d: d.time_in_prediction, reverse=True)
        print(f"\nTop 5 most expensive decisions:")
        for i, dec in enumerate(sorted_decisions[:5]):
            print(f"  {i+1}. Decision {dec.decision}: {dec.time_in_prediction} ns, "
                  f"{dec.invocations} invocations, "
                  f"{dec.ambiguity_count} ambiguities")
        
        # Verify some basic properties
        self.assertGreater(len(decisions), 0, "Should have at least one decision")
        self.assertGreaterEqual(profile.total_time_in_prediction, 0)
        
    def test_profiling_disabled(self):
        """Test that profiling returns None when disabled"""
        parser = Parser()
        # Don't enable profiling
        
        parser.parses([
            ("test.pss", """
             component pss_top {
                 action A { }
             }
             """),
        ])
        
        # Get profiling info - should be None
        profile = parser.get_profile_info()
        
        self.assertIsNone(profile, "Profile info should be None when profiling is not enabled")

    def test_profiling_complex(self):
        """Test profiling with more complex grammar"""
        parser = Parser()
        parser.enable_profiling(True)
        
        parser.parses([
            ("complex.pss", """
             component pss_top {
                 action A {
                     rand int x;
                     rand int y;
                     
                     constraint {
                         x > 0 && x < 100;
                         y == x * 2;
                         x + y < 200;
                     }
                     
                     exec body {
                         int z = x + y;
                     }
                 }
                 
                 action B {
                     rand int a;
                     rand int b;
                     
                     constraint {
                         a > 0;
                         b == a * 3;
                     }
                     
                     exec body {
                         int result = a + b;
                     }
                 }
                 
                 action C {
                     A a1;
                     B b1;
                     
                     activity {
                         a1;
                         b1;
                     }
                 }
             }
             """),
        ])
        
        profile = parser.get_profile_info()
        self.assertIsNotNone(profile)
        
        decisions = profile.get_decision_info()
        print(f"\n=== Complex Parse Results ===")
        print(f"Total decisions: {len(decisions)}")
        print(f"Total time: {profile.total_time_in_prediction} ns")
        
        # Check for LL fallback
        ll_decisions = profile.get_ll_decisions()
        if ll_decisions:
            print(f"Decisions requiring LL fallback: {len(ll_decisions)}")
            print(f"  Decision numbers: {ll_decisions[:10]}")  # Show first 10
        
        # Count ambiguities
        total_ambiguities = sum(d.ambiguity_count for d in decisions)
        if total_ambiguities > 0:
            print(f"Total ambiguities detected: {total_ambiguities}")

if __name__ == '__main__':
    unittest.main()
